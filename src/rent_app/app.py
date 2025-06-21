from __future__ import annotations

import json
from os import environ
import sqlite3
import datetime
import urllib.parse
import importlib.resources

import boto3
from jinja2 import Environment, PackageLoader, select_autoescape

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_boto3_s3.service_resource import S3ServiceResource

# Key off single environment variable to determine configuration
# Migrate to config file if this section gets unwieldy
VALID_STAGES = ["prod"]
STAGE = environ["STAGE"]
ISLOCAL = environ.get("ISLOCAL", "").lower() == "true"
BUCKET_NAME = f"rentapp-{STAGE}-persistence-bucket"

# Declare singletons -- we'll cache these here for faster warm invocations
db = None
s3_client = None


def get_db_and_s3() -> tuple[sqlite3.Connection, S3ServiceResource]:
    """Get cached database and s3 connections, initializing them if needed

    We're lazy loding the s3 client and the database -- we can just dummy
    store the database in s3 and pull it out here because we're guaranteeing
    concurrency = 1 -- we will never have more than one lambda instance
    attempting to interact with this database, so it doesn't matter that
    we're just uploading an downloading an entire file (instead of doing
    some sort of intelligent access)
    """
    global db, s3_client

    if s3_client is None:
        s3_client = boto3.resource("s3")
    if db is None:
        if ISLOCAL:
            db_location = "../database.db"
        else:
            # /tmp is a writable location on lambda (unlike /var, where our cwd is)
            db_location = "/tmp/database.db"
            s3_client.Object(BUCKET_NAME, "database.db").download_file(db_location)

        db = sqlite3.connect(db_location)
        db.row_factory = sqlite3.Row

    return db, s3_client


def lambda_handler(event, context):
    global db
    global s3_client
    local_resources = importlib.resources.files()
    method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    if method == "GET":
        print("GET Request")

        if path == "/stylesheet.css":
            # Serve CSS file
            css_content = local_resources.joinpath(
                "templates", "stylesheet.css"
            ).read_text()
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/css"},
                "body": css_content,
            }
        elif path == "/":
            # Serve main page
            # TODO make this passed by client
            month = datetime.datetime.now().isoformat()
            db, _ = get_db_and_s3()
            cur = db.cursor()
            cur.execute(
                local_resources.joinpath("get_rents.sql").read_text(), {"month": month}
            )
            rents = cur.fetchall()
            print([*rents])
            env = Environment(
                loader=PackageLoader("rent_app"), autoescape=select_autoescape()
            )
            template = env.get_template("index.jinja")
            print(template.render({"rents": rents}))
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({"rents": rents}),
            }
    elif method == "POST":
        print("POST Request")
        if path == "/":
            # Handle rent collection form submission
            db, s3_client = get_db_and_s3()

            # Parse form data from request body
            body = event.get("body", "")
            form_data = urllib.parse.parse_qs(body)

            cur = db.cursor()
            month = datetime.datetime.now().isoformat()
            collected_on = datetime.date.today().isoformat()

            # Collect all records to insert
            records_to_insert = []
            for lease_id, values in form_data.items():
                if values and values[0]:
                    amount = float(values[0])

                    if amount > 0:  # Only insert records for non-zero amounts
                        records_to_insert.append(
                            (lease_id, amount, month, collected_on)
                        )

            # Batch insert all records
            if records_to_insert:
                cur.executemany(
                    """INSERT INTO CollectedRent (lease, amount, collected_for, collected_on) 
                       VALUES (?, ?, date(?, 'start of month'), ?)""",
                    records_to_insert,
                )
                db.commit()

                # Upload updated database back to S3 if not local
                if not ISLOCAL:
                    s3_client.Object(BUCKET_NAME, "database.db").upload_file(
                        "/tmp/database.db"
                    )

            # Redirect back to GET page (PRG pattern)
            return {"statusCode": 302, "headers": {"Location": "/"}, "body": ""}
    return {"statusCode": 200, "body": json.dumps(event)}


if __name__ == "__main__":
    lambda_handler({"requestContext": {"http": {"method": "GET", "path": "/"}}}, None)

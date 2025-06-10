import json
from os import environ
import sqlite3
import datetime
from pathlib import Path

import boto3
from jinja2 import Environment, PackageLoader, select_autoescape

# Key off single environment variable to determine configuration
# Migrate to config file if this section gets unwieldy
VALID_STAGES = ["prod"]
STAGE = environ["STAGE"]
ISLOCAL = environ.get("ISLOCAL", "").lower() == "true"
BUCKET_NAME = f"rentapp-{STAGE}-persistence-bucket"

# Declare singletons -- we'll cache these here for faster warm invocations
db = None
s3_client = None


def lambda_handler(event, context):
    global db
    global s3_client
    method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    if method == "GET":
        print("GET Request")

        if path == "/stylesheet.css":
            # Serve CSS file
            css_content = Path("templates/stylesheet.css").read_text()
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/css"},
                "body": css_content,
            }
        elif path == "/":
            # Serve main page
            # TODO make this passed by client
            month = datetime.datetime.now().isoformat()
            # We're lazy loding the s3 client and the database -- we can just dummy
            # store the database in s3 and pull it out here because we're guaranteeing
            # concurrency = 1 -- we will never have more than one lambda instance
            # attempting to interact with this database, so it doesn't matter that
            # we're just uploading an downloading an entire file (instead of doing
            # some sort of intelligent access)
            if db is None:
                if ISLOCAL:
                    db_location = "../database.db"
                else:
                    if s3_client is None:
                        s3_client = boto3.resource("s3")
                    # /tmp is a writable location on lambda (unlike /var, where our cwd is)
                    db_location = "/tmp/database.db"
                    s3_client.Object(BUCKET_NAME, "database.db").download_file(
                        db_location
                    )
                db = sqlite3.connect(db_location)
                db.row_factory = sqlite3.Row
            cur = db.cursor()
            cur.execute(Path("get_rents.sql").read_text(), {"month": month})
            rents = cur.fetchall()
            print([*rents])
            env = Environment(
                loader=PackageLoader("app"), autoescape=select_autoescape()
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
    return {"statusCode": 200, "body": json.dumps(event)}


if __name__ == "__main__":
    lambda_handler({"requestContext": {"http": {"method": "GET", "path": "/"}}}, None)

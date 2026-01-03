from __future__ import annotations

import json
from os import environ
import sqlite3
import datetime
import urllib.parse
import importlib.resources
import base64

import boto3
from jinja2 import Environment, PackageLoader, select_autoescape

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_boto3_s3.service_resource import S3ServiceResource

# Key off single environment variable to determine configuration
# Migrate to config file if this section gets unwieldy
VALID_STAGES = ["prod"]
STAGE = environ["STAGE"]
ISLOCAL = environ.get("ISLOCAL", "").lower()
BUCKET_NAME = f"rentapp-{STAGE}-persistence-bucket"
S3_DOWNLOAD_LOCATION = "/tmp/database.db"

# Declare singletons -- we'll cache these here for faster warm invocations
db = None
s3_client = None


def upload_db_to_s3() -> None:
    """Upload local database back to S3 if not in local mode"""
    if not ISLOCAL:
        _, s3 = get_db_and_s3()
        s3.Object(BUCKET_NAME, "database.db").upload_file(S3_DOWNLOAD_LOCATION)


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
            db_location = ISLOCAL
        else:
            # /tmp is a writable location on lambda (unlike /var, where our cwd is)
            db_location = S3_DOWNLOAD_LOCATION
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
        print(f"GET Request for {path}")
        if path == "/stylesheet.css":
            # Serve CSS file
            print("Serving CSS file")
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
            query_parameters = event.get("queryStringParameters", {})
            current_date = datetime.date.today()
            month = int(query_parameters.get("month", current_date.month))
            year = int(query_parameters.get("year", current_date.year))
            # TODO make this passed by client
            selected_date = datetime.date(year, month, 1)
            db, _ = get_db_and_s3()
            cur = db.cursor()
            cur.execute(
                local_resources.joinpath("get_rents.sql").read_text(), {"month": selected_date.isoformat()}
            )
            rents = cur.fetchall()
            env = Environment(
                loader=PackageLoader("rent_app"), autoescape=select_autoescape()
            )
            template = env.get_template("index.jinja")
            body = template.render({"rents": rents, "selected_date": selected_date})
            print(body)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": body,
            }
    elif method == "POST":
        print("POST Request")
        if path == "/":
            # Handle rent collection form submission
            db, s3_client = get_db_and_s3()

            # Parse form data from request body
            body = event.get("body", "")
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            form_data = urllib.parse.parse_qs(body)

            cur = db.cursor()
            month = datetime.datetime.now().isoformat()
            collected_on = datetime.date.today().isoformat()

            # Collect all records to insert
            records_to_insert = []
            for lease_id, values in form_data.items():
                if values and values[0]:
                    amount = float(values[0])
                    lease_id = int(lease_id)
                    if amount > 0:  # Only insert records for non-zero amounts
                        records_to_insert.append(
                            (lease_id, amount, month, collected_on)
                        )
            # Batch insert all records
            if records_to_insert:
                print(f"{len(records_to_insert)} records found")
                cur.executemany(
                    """INSERT INTO CollectedRent (lease, amount, collected_for, collected_on)
                       VALUES (?, ?, date(?, 'start of month'), ?)""",
                    records_to_insert,
                )
                db.commit()

                # Upload updated database back to S3 if not local
                if not ISLOCAL:
                    print("Uploading to S3")
                    s3_client.Object(BUCKET_NAME, "database.db").upload_file(
                        S3_DOWNLOAD_LOCATION
                    )

            # Redirect back to GET page (PRG pattern)
            return {"statusCode": 302, "headers": {"Location": "/"}, "body": ""}

    # Admin routes
    env = Environment(loader=PackageLoader("rent_app"), autoescape=select_autoescape())

    if path == "/admin":
        if method == "GET":
            db, _ = get_db_and_s3()
            cur = db.cursor()
            # Get counts for dashboard
            cur.execute("SELECT COUNT(*) as cnt FROM Unit WHERE deleted_on IS NULL")
            unit_count = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM Tenant WHERE deleted_on IS NULL")
            tenant_count = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM Lease WHERE deleted_on IS NULL")
            lease_count = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM CollectedRent WHERE deleted_on IS NULL")
            rent_count = cur.fetchone()["cnt"]
            template = env.get_template("admin.jinja")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({
                    "unit_count": unit_count,
                    "tenant_count": tenant_count,
                    "lease_count": lease_count,
                    "rent_count": rent_count,
                }),
            }

    elif path.startswith("/admin/units"):
        db, _ = get_db_and_s3()
        cur = db.cursor()
        if method == "GET":
            cur.execute("SELECT id, address, created_on FROM Unit WHERE deleted_on IS NULL ORDER BY created_on DESC")
            units = cur.fetchall()
            template = env.get_template("admin_units.jinja")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({"units": units}),
            }
        elif method == "POST":
            body = event.get("body", "")
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            form_data = urllib.parse.parse_qs(body)

            if path == "/admin/units":
                address = form_data.get("address", [""])[0]
                if address:
                    cur.execute("INSERT INTO Unit (address) VALUES (?)", (address,))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/units/edit":
                unit_id = form_data.get("id", [""])[0]
                address = form_data.get(f"address_{unit_id}", [""])[0]
                if unit_id and address:
                    cur.execute("UPDATE Unit SET address = ? WHERE id = ? AND deleted_on IS NULL", (address, int(unit_id)))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/units/delete":
                unit_id = form_data.get("id", [""])[0]
                if unit_id:
                    cur.execute("SELECT COUNT(*) as cnt FROM Tenant WHERE unit = ? AND deleted_on IS NULL", (int(unit_id),))
                    if cur.fetchone()["cnt"] == 0:
                        cur.execute("UPDATE Unit SET deleted_on = CURRENT_TIMESTAMP WHERE id = ?", (int(unit_id),))
                        db.commit()
                        upload_db_to_s3()
            return {"statusCode": 302, "headers": {"Location": "/admin/units"}, "body": ""}

    elif path.startswith("/admin/tenants"):
        db, _ = get_db_and_s3()
        cur = db.cursor()
        if method == "GET":
            cur.execute("""
                SELECT t.id, t.name, t.unit, u.address as unit_address, t.created_on
                FROM Tenant t
                JOIN Unit u ON t.unit = u.id
                WHERE t.deleted_on IS NULL
                ORDER BY t.created_on DESC
            """)
            tenants = cur.fetchall()
            cur.execute("SELECT id, address FROM Unit WHERE deleted_on IS NULL ORDER BY address")
            units = cur.fetchall()
            template = env.get_template("admin_tenants.jinja")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({"tenants": tenants, "units": units}),
            }
        elif method == "POST":
            body = event.get("body", "")
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            form_data = urllib.parse.parse_qs(body)

            if path == "/admin/tenants":
                name = form_data.get("name", [""])[0]
                unit = form_data.get("unit", [""])[0]
                if name and unit:
                    cur.execute("INSERT INTO Tenant (name, unit) VALUES (?, ?)", (name, int(unit)))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/tenants/edit":
                tenant_id = form_data.get("id", [""])[0]
                name = form_data.get(f"name_{tenant_id}", [""])[0]
                unit = form_data.get(f"unit_{tenant_id}", [""])[0]
                if tenant_id and name and unit:
                    cur.execute("UPDATE Tenant SET name = ?, unit = ? WHERE id = ? AND deleted_on IS NULL", (name, int(unit), int(tenant_id)))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/tenants/delete":
                tenant_id = form_data.get("id", [""])[0]
                if tenant_id:
                    cur.execute("SELECT COUNT(*) as cnt FROM Lease WHERE tenant = ? AND deleted_on IS NULL", (int(tenant_id),))
                    if cur.fetchone()["cnt"] == 0:
                        cur.execute("UPDATE Tenant SET deleted_on = CURRENT_TIMESTAMP WHERE id = ?", (int(tenant_id),))
                        db.commit()
                        upload_db_to_s3()
            return {"statusCode": 302, "headers": {"Location": "/admin/tenants"}, "body": ""}

    elif path.startswith("/admin/leases"):
        db, _ = get_db_and_s3()
        cur = db.cursor()
        if method == "GET":
            cur.execute("""
                SELECT l.id, l.tenant, t.name as tenant_name, u.address as unit_address,
                       l.rent, l.start_date, l.end_date, l.created_on
                FROM Lease l
                JOIN Tenant t ON l.tenant = t.id
                JOIN Unit u ON t.unit = u.id
                WHERE l.deleted_on IS NULL
                ORDER BY l.start_date DESC
            """)
            leases = cur.fetchall()
            cur.execute("""
                SELECT t.id, t.name, u.address
                FROM Tenant t
                JOIN Unit u ON t.unit = u.id
                WHERE t.deleted_on IS NULL
                ORDER BY u.address, t.name
            """)
            tenants = cur.fetchall()
            template = env.get_template("admin_leases.jinja")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({"leases": leases, "tenants": tenants}),
            }
        elif method == "POST":
            body = event.get("body", "")
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            form_data = urllib.parse.parse_qs(body)

            if path == "/admin/leases":
                tenant = form_data.get("tenant", [""])[0]
                rent = form_data.get("rent", [""])[0]
                start_date = form_data.get("start_date", [""])[0]
                end_date = form_data.get("end_date", [""])[0] or None
                if tenant and rent and start_date:
                    cur.execute("INSERT INTO Lease (tenant, rent, start_date, end_date) VALUES (?, ?, ?, ?)",
                                (int(tenant), float(rent), start_date, end_date))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/leases/edit":
                lease_id = form_data.get("id", [""])[0]
                tenant = form_data.get(f"tenant_{lease_id}", [""])[0]
                rent = form_data.get(f"rent_{lease_id}", [""])[0]
                start_date = form_data.get(f"start_date_{lease_id}", [""])[0]
                end_date = form_data.get(f"end_date_{lease_id}", [""])[0] or None
                if lease_id and tenant and rent and start_date:
                    cur.execute("UPDATE Lease SET tenant = ?, rent = ?, start_date = ?, end_date = ? WHERE id = ? AND deleted_on IS NULL",
                                (int(tenant), float(rent), start_date, end_date, int(lease_id)))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/leases/delete":
                lease_id = form_data.get("id", [""])[0]
                if lease_id:
                    cur.execute("SELECT COUNT(*) as cnt FROM CollectedRent WHERE lease = ? AND deleted_on IS NULL", (int(lease_id),))
                    if cur.fetchone()["cnt"] == 0:
                        cur.execute("UPDATE Lease SET deleted_on = CURRENT_TIMESTAMP WHERE id = ?", (int(lease_id),))
                        db.commit()
                        upload_db_to_s3()
            return {"statusCode": 302, "headers": {"Location": "/admin/leases"}, "body": ""}

    elif path.startswith("/admin/rents"):
        db, _ = get_db_and_s3()
        cur = db.cursor()
        if method == "GET":
            cur.execute("""
                SELECT cr.id, cr.lease, cr.amount, cr.collected_for, cr.collected_on, cr.created_on,
                       t.name as tenant_name, u.address as unit_address, l.rent as lease_rent
                FROM CollectedRent cr
                JOIN Lease l ON cr.lease = l.id
                JOIN Tenant t ON l.tenant = t.id
                JOIN Unit u ON t.unit = u.id
                WHERE cr.deleted_on IS NULL
                ORDER BY cr.collected_for DESC, cr.collected_on DESC
            """)
            rents = cur.fetchall()
            cur.execute("""
                SELECT l.id, l.rent, l.start_date, t.name as tenant_name, u.address
                FROM Lease l
                JOIN Tenant t ON l.tenant = t.id
                JOIN Unit u ON t.unit = u.id
                WHERE l.deleted_on IS NULL
                ORDER BY u.address, t.name
            """)
            leases = cur.fetchall()
            template = env.get_template("admin_rents.jinja")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": template.render({"rents": rents, "leases": leases}),
            }
        elif method == "POST":
            body = event.get("body", "")
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            form_data = urllib.parse.parse_qs(body)

            if path == "/admin/rents":
                lease = form_data.get("lease", [""])[0]
                amount = form_data.get("amount", [""])[0]
                collected_for = form_data.get("collected_for", [""])[0]
                collected_on = form_data.get("collected_on", [""])[0]
                if lease and amount and collected_for and collected_on:
                    cur.execute("INSERT INTO CollectedRent (lease, amount, collected_for, collected_on) VALUES (?, ?, date(?, 'start of month'), ?)",
                                (int(lease), float(amount), collected_for, collected_on))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/rents/edit":
                rent_id = form_data.get("id", [""])[0]
                lease = form_data.get(f"lease_{rent_id}", [""])[0]
                amount = form_data.get(f"amount_{rent_id}", [""])[0]
                collected_for = form_data.get(f"collected_for_{rent_id}", [""])[0]
                collected_on = form_data.get(f"collected_on_{rent_id}", [""])[0]
                if rent_id and lease and amount and collected_for and collected_on:
                    cur.execute("UPDATE CollectedRent SET lease = ?, amount = ?, collected_for = date(?, 'start of month'), collected_on = ? WHERE id = ? AND deleted_on IS NULL",
                                (int(lease), float(amount), collected_for, collected_on, int(rent_id)))
                    db.commit()
                    upload_db_to_s3()
            elif path == "/admin/rents/delete":
                rent_id = form_data.get("id", [""])[0]
                if rent_id:
                    cur.execute("UPDATE CollectedRent SET deleted_on = CURRENT_TIMESTAMP WHERE id = ?", (int(rent_id),))
                    db.commit()
                    upload_db_to_s3()
            return {"statusCode": 302, "headers": {"Location": "/admin/rents"}, "body": ""}

    return {"statusCode": 200, "body": json.dumps(event)}


if __name__ == "__main__":
    lambda_handler({"requestContext": {"http": {"method": "GET", "path": "/"}}}, None)

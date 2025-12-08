import pytest
import sqlite3
from pathlib import Path
import os
import importlib.resources
import datetime

import rent_app

db_path = Path(os.environ["ISLOCAL"])

@pytest.fixture(autouse=True)
def setup_db(base_db_bytes: bytes):
    db_path.write_bytes(base_db_bytes)


def test_stylesheet():
    true_css = (
        importlib.resources.files(rent_app)
        .joinpath("templates", "stylesheet.css")
        .read_text()
    )
    response = rent_app.lambda_handler(
        {"requestContext": {"http": {"method": "GET", "path": "/stylesheet.css"}}}, None
    )
    test_css = response["body"]
    status_code = response["statusCode"]
    content_type = response["headers"]["Content-Type"]
    assert test_css == true_css
    assert status_code == 200
    assert content_type == "text/css"


def test_homepage():
    response = rent_app.lambda_handler(
        {"requestContext": {"http": {"method": "GET", "path": "/"}}}, None
    )
    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/html"

def test_no_collected_rents_shows_full_rent_remaining():
    get_rents_sql = (
        importlib.resources.files(rent_app)
        .joinpath("get_rents.sql")
        .read_text()
    )
    check_no_collected_rents = "SELECT COUNT(1) FROM CollectedRent WHERE collected_on > '2100-01-01'"
    db = sqlite3.connect(db_path)
    num_collected_rents = db.execute(check_no_collected_rents).fetchall()[0][0]
    assert num_collected_rents == 0

    rents = db.execute(get_rents_sql, {"month": datetime.datetime.now().isoformat()}).fetchall()
    assert rents[0][3] == rents[0][2]

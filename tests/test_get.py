import pytest
import sqlite3
from pathlib import Path
import os


import rent_app


@pytest.fixture(autouse=True)
def setup_db(base_db_bytes: bytes):
    db_path = Path(os.environ["ISLOCAL"])
    db_path.write_bytes(base_db_bytes)


def test_stylesheet():
    import importlib.resources

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

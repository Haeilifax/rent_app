import sqlite3
from pathlib import Path

import pytest

import rent_app


@pytest.fixture(scope="module")
def base_db_bytes(tmp_path_factory):
    db_path: Path = tmp_path_factory.mktemp("data") / "database.db"
    db = sqlite3.connect(db_path)
    db.executescript(Path("database/ddl.sql").read_text())
    db.executescript(Path("database/test_data.sql").read_text())
    db.commit()
    return db_path.read_bytes()


@pytest.fixture(autouse=True)
def setup_db(base_db_bytes: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "database.db"
    db_path.write_bytes(base_db_bytes)
    monkeypatch.setenv("ISLOCAL", str(db_path.absolute()))


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

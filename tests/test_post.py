import pytest
import sqlite3
from pathlib import Path
import os

import rent_app


@pytest.fixture(autouse=True)
def setup_db(base_db_bytes: bytes):
    db_path = Path(os.environ["ISLOCAL"])
    db_path.write_bytes(base_db_bytes)


def test_add_collected_rent():
    response = rent_app.lambda_handler(
        {
            "requestContext": {"http": {"method": "POST", "path": "/"}},
            "body": "1=500",
        },
        None,
    )
    db_path = Path(os.environ["ISLOCAL"])
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT lease, amount FROM CollectedRent")
    data = cur.fetchall()
    found_row = False
    for datum in data:
        if datum["lease"] == 1 and datum["amount"] == 500:
            found_row = True
    assert found_row
    assert response["statusCode"] == 302

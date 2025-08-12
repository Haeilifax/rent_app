import pytest
import sqlite3
from pathlib import Path
import os
import tempfile


# Two functions, second to allow the raw bytes to be used as a fixture
@pytest.hookimpl
def pytest_sessionstart():
    db_path = Path(tempfile.mkstemp("database.db")[1])
    db = sqlite3.connect(db_path)
    db.executescript(Path("database/ddl.sql").read_text())
    db.executescript(Path("database/test_data.sql").read_text())
    db.commit()
    os.environ["ISLOCAL"] = str(db_path.absolute())


@pytest.fixture(scope="module")
def base_db_bytes():
    db_path = Path(os.environ["ISLOCAL"])
    return db_path.read_bytes()


@pytest.hookimpl
def pytest_sessionfinish():
    db_path = Path(os.environ["ISLOCAL"])
    db_path.unlink()

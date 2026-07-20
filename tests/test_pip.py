#!/usr/bin/env python3
import hashlib
import json
import sqlite3
from pathlib import Path
from importlib.resources import files


PACKAGE_FILES = {
    "lang.json": None,
    "osint/SiteRegistry.db": None,
    "banner": None
}


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def get_package_files() -> dict:
    result = {}
    package_dir = files("scratrace")
    for filename in PACKAGE_FILES:
        try:
            file_path = package_dir.joinpath(filename)
            if file_path.is_file():
                result[filename] = str(file_path)
        except (FileNotFoundError, TypeError):
            pass
    return result


def test_package_files_exist():
    paths = get_package_files()
    missing = [f for f in PACKAGE_FILES if f not in paths]
    assert not missing, f"Missing package files: {missing}"


def test_lang_json_valid():
    paths = get_package_files()
    if "lang.json" not in paths:
        return
    with open(paths["lang.json"], "r", encoding="utf-8") as f:
        json.load(f)


def test_db_valid():
    paths = get_package_files()
    if "SiteRegistry.db" not in paths:
        return
    path = Path(paths["SiteRegistry.db"])
    assert path.stat().st_size > 0
    con = sqlite3.connect(path)
    con.execute("SELECT 1").fetchone()
    con.close()

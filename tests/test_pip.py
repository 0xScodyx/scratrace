#!/usr/bin/env python3
import hashlib
import json
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


def get_expected_hashes() -> dict:
    hashes_file = Path(__file__).resolve().parent / ".expected_hashes.json"
    if not hashes_file.exists():
        return {}
    with open(hashes_file, "r") as f:
        return json.load(f)


def test_package_files_exist():
    paths = get_package_files()
    missing = [f for f in PACKAGE_FILES if f not in paths]
    assert not missing, f"Missing package files: {missing}"


def test_package_files_match_expected():
    paths = get_package_files()
    expected = get_expected_hashes()
    
    for filename, path_str in paths.items():
        actual = sha256_file(Path(path_str))
        expected_hash = expected.get(filename)
        
        if expected_hash is None:
            continue
            
        assert actual == expected_hash, \
            f"{filename} hash mismatch.\n  Expected: {expected_hash}\n  Actual:   {actual}"

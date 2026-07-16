import sys
from pathlib import Path

_BANNER_PATH = Path(__file__).with_name("banner")


def print_banner() -> None:
    sys.stdout.buffer.write(_BANNER_PATH.read_bytes())
    sys.stdout.flush()

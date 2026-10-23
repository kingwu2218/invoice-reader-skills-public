# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create custom.md with the default document buckets, not yet confirmed by the user.

Usage: uv run new_custom.py [path]   (default: custom.md)
"""

import sys
from pathlib import Path

from buckets import default_text


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "custom.md")
    if path.exists():
        print(f"'{path}' already exists, so it was left as it is.")
        return 1
    path.write_bytes(default_text(confirmed=False).encode("utf-8"))
    print(f"Created '{path}' with the default document buckets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

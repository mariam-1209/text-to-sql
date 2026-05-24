"""
Downloads the Chinook sample SQLite database.
Run once before launching the app:  python setup_db.py
"""
import os
import sys
import urllib.request

# The Chinook DB lives in lerocha/chinook-database on GitHub.
# If this URL 404s, the repo was reorganized — go to
# https://github.com/lerocha/chinook-database and find the current path
# to the .sqlite file under ChinookDatabase/DataSources/.
CHINOOK_URL = (
    "https://github.com/lerocha/chinook-database/raw/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)
OUTPUT_PATH = "chinook.db"


def main():
    if os.path.exists(OUTPUT_PATH):
        print(f"{OUTPUT_PATH} already exists. Delete it first to re-download.")
        return
    print(f"Downloading Chinook database from:\n  {CHINOOK_URL}")
    try:
        urllib.request.urlretrieve(CHINOOK_URL, OUTPUT_PATH)
    except Exception as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        print(
            "\nFallback: manually download a Chinook SQLite file from\n"
            "  https://github.com/lerocha/chinook-database\n"
            f"and save it as {OUTPUT_PATH} in this folder.",
            file=sys.stderr,
        )
        sys.exit(1)
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"Saved to {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

"""Entry point run by GitHub Actions every 10 minutes."""
import os
import shutil
import sys
import tempfile
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .downloader import download_reel
from .drive import upload_file
from .queue_logic import process
from .sheets_store import SheetStore

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
TIME_BUDGET_SECONDS = 12 * 60  # stop starting new attempts after 12 min


def need(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Missing GitHub secret: {name}")
    return value


def main():
    creds = Credentials(
        None,
        refresh_token=need("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=need("GOOGLE_CLIENT_ID"),
        client_secret=need("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    store = SheetStore(sheets, need("SHEET_ID"))
    folder_id = need("DRIVE_FOLDER_ID")

    work = tempfile.mkdtemp(prefix="reels_")
    cookies_path = None
    cookies_text = os.environ.get("FB_COOKIES", "").strip()
    if cookies_text:
        cookies_path = os.path.join(work, "cookies.txt")
        with open(cookies_path, "w") as fh:
            fh.write(cookies_text + "\n")

    counter = {"n": 0}

    def download(link):
        counter["n"] += 1
        sub = os.path.join(work, f"dl{counter['n']}")
        os.makedirs(sub)
        return download_reel(link, sub, cookies_path)

    def upload(path):
        return upload_file(drive, folder_id, path)

    try:
        result = process(
            store, download, upload,
            log=lambda m: print(m, flush=True),
            deadline=time.monotonic() + TIME_BUDGET_SECONDS,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"Run finished: {result}")
    return 1 if result == "upload_error" else 0


if __name__ == "__main__":
    sys.exit(main())

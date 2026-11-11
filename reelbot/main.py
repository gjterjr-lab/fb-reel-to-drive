"""Entry point run by GitHub Actions.

  python -m reelbot.main           one pass over the queue
  python -m reelbot.main --loop    keep going: one pass, wait 10 minutes, repeat
"""
import os
import shutil
import sys
import tempfile
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .downloader import download_reel
from .drive import upload_file
from .loop import run_loop
from .queue_logic import process
from .sheets_store import SheetStore

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
PASS_BUDGET_SECONDS = 8 * 60  # stop starting new attempts after 8 min inside one pass


def need(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Missing GitHub secret: {name}")
    return value


def make_runner():
    creds = Credentials(
        None,
        refresh_token=need("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=need("GOOGLE_CLIENT_ID"),
        client_secret=need("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    sheet_id = need("SHEET_ID")
    folder_id = need("DRIVE_FOLDER_ID")
    cookies_text = os.environ.get("FB_COOKIES", "").strip()

    def run_pass():
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        store = SheetStore(sheets, sheet_id)

        work = tempfile.mkdtemp(prefix="reels_")
        cookies_path = None
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
            return process(
                store, download, upload,
                log=lambda m: print(m, flush=True),
                deadline=time.monotonic() + PASS_BUDGET_SECONDS,
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    return run_pass


def main():
    run_pass = make_runner()
    if "--loop" in sys.argv[1:]:
        return run_loop(run_pass, log=lambda m: print(m, flush=True))
    result = run_pass()
    print(f"Run finished: {result}")
    return 1 if result == "upload_error" else 0


if __name__ == "__main__":
    sys.exit(main())

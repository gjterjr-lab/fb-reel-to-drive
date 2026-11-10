# Facebook reel to Google Drive queue

Paste a Facebook reel link into a small web page. Every ~10 minutes a GitHub Action
picks one link, downloads the reel in the best quality (yt-dlp) and uploads it to a
Google Drive folder you choose. Nothing private is stored in this repo.

## How it works

- Add-link page (Google Apps Script, in your Google account) -> writes into a private Google Sheet (tabs: Queue, Failed)
- GitHub Action (every 10 min) -> reads the Sheet, downloads with yt-dlp, uploads to your Drive folder, deletes the link

Queue rules (each run):
1. Look at **Queue** first. Take the first link.
2. Download fails: link goes to the **end of Failed**, the next link is tried **right away**.
3. Download works: uploaded to Drive, link deleted, run ends, **wait ~10 min**.
4. Queue empty: retry **Failed** from the top. A Failed link that fails again goes to the end.
   Each Failed link is tried once per run, and the Queue is re-checked before every attempt.
5. If Drive itself is failing (not the link), the link stays where it is and the run turns red.

## Privacy (safe to make this repo public)

- Links, Drive folder ID, sheet ID and Google keys are NOT in the code. Keys live in
  GitHub Secrets; links live in your private Google Sheet.
- The logs never print links, only a short anonymous code like #a3f9c1.
- Forks and pull requests cannot read your secrets.

## One-time setup (about 20 minutes)

### 1. Google Sheet + add-link page
1. Create a new Google Sheet named Reel Queue. Copy its ID from the URL
   (docs.google.com/spreadsheets/d/THIS_PART/edit).
2. In the sheet: Extensions > Apps Script.
3. Replace the contents of Code.gs with apps-script/Code.gs from this repo.
4. Click + next to Files > HTML, name it exactly `Index`, paste apps-script/Index.html.
5. Deploy > New deployment > type: Web app. Execute as: Me. Who has access: Only myself.
6. Authorize when asked (Advanced > continue), then copy the Web app URL.
   Open it on your phone and use Add to Home screen. That is your link bar.

### 2. Drive folder
Create (or pick) the Drive folder. Its ID is the last part of the folder URL
(drive.google.com/drive/folders/THIS_PART).

### 3. Google keys (lets the Action use your Drive + Sheet)
1. Go to https://console.cloud.google.com and create a project.
2. APIs & Services > Library: enable Google Drive API and Google Sheets API.
3. OAuth consent screen: User type External, fill name/email, then Publish app > In production.
   (In "Testing" mode the key expires after 7 days.)
4. Credentials > Create credentials > OAuth client ID > Web application.
   Add this Authorized redirect URI: https://developers.google.com/oauthplayground
   Copy the Client ID and Client secret.
5. Open https://developers.google.com/oauthplayground
   - Gear icon > tick Use your own OAuth credentials > paste Client ID and secret.
   - In the left box type these two scopes and press Authorize APIs:
     https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets
   - Sign in, allow, then Exchange authorization code for tokens.
   - Copy the Refresh token.

### 4. GitHub secrets
Repo > Settings > Secrets and variables > Actions > New repository secret:

| Name | Value |
|---|---|
| GOOGLE_CLIENT_ID | from step 3 |
| GOOGLE_CLIENT_SECRET | from step 3 |
| GOOGLE_REFRESH_TOKEN | from step 3 |
| DRIVE_FOLDER_ID | from step 2 |
| SHEET_ID | from step 1 |
| FB_COOKIES | optional, see below |

### 5. Test
Add one reel link on your page, then Actions > Reel queue > Run workflow.
After about a minute the video should be in your Drive folder and the link gone from the sheet.
From then on it runs by itself every 10 minutes.

## Going public later
Settings > General > Danger Zone > Change visibility > Public. Public repos get unlimited
Actions minutes (a private repo only has 2,000 min/month, far too little for a 10-minute schedule).
GitHub pauses schedules in public repos after 60 days without repo activity. A step in the
workflow tries to prevent that; if it ever stops, click Enable workflow in the Actions tab.

## If many reels fail
Facebook sometimes blocks cloud servers. Fix: export cookies from a Facebook account
(browser extension "Get cookies.txt LOCALLY", Netscape format) and paste the whole file into the
FB_COOKIES secret. A spare account is safer than your main one. Private, deleted or friends-only
reels will keep failing; delete their rows from the Failed tab.

## Files
- .github/workflows/reel-queue.yml - the 10 minute schedule
- reelbot/queue_logic.py - the queue/failed rules
- reelbot/downloader.py - yt-dlp, best quality, mp4
- reelbot/drive.py, reelbot/sheets_store.py - Google Drive and Sheet access
- apps-script/ - the add-link page (lives in your Google account, not run from GitHub)
- tests/ - python -m unittest discover tests

Use it only for content you are allowed to save.

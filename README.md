# Facebook reel to Google Drive queue

Paste a Facebook reel link into a small web page. A GitHub Action picks one link every
10 minutes, downloads the reel in the best quality (yt-dlp) and uploads it to a Google
Drive folder you choose. Nothing private is stored in this repo.

## How it works

- Add-link page (Google Apps Script, in your Google account) writes into a private Google Sheet (tabs: Queue, Failed).
- One GitHub job stays alive for about 5h20m and loops by itself: one pass over the queue, wait 10 minutes, repeat.
  At the end it starts the next job, so the loop never stops. (GitHub's own timer proved unreliable,
  with gaps of 30 to 80 minutes, which is why the job keeps its own clock.)
- An hourly schedule is only a safety net: it restarts the loop if the chain ever breaks.
- Runs never overlap.

Queue rules (each pass):
1. Look at **Queue** first. Take the first link.
2. Download fails: link goes to the **end of Failed**, the next link is tried **right away**.
3. Download works: uploaded to Drive, link deleted, pass ends, **wait 10 min**.
4. Queue empty: retry **Failed** from the top. A Failed link that fails again goes to the end.
   Each Failed link is tried once per pass, and the Queue is re-checked before every attempt.
5. If Drive itself is failing (not the link), the link stays where it is. After 3 failing
   passes in a row the run turns red (GitHub emails you) and the loop stops until the hourly
   safety net starts a new one.

## Good to know

- The Actions tab shows one long run most of the time instead of many short ones.
  Open it and look at the log: one line per pass, like `Round 7: success`.
- To pause everything: Actions > Reel queue > cancel the running job, then "..." > Disable workflow.
  To resume: Enable workflow, then Run workflow.
- To test a change by hand, cancel the running job first, otherwise a manual run waits in line.
- A pass that ends in `Run finished` / `Round N: error` with a red run usually means the Google
  key expired (see below) or a secret is wrong.

## Privacy (this repo is public)

- Links, Drive folder ID, sheet ID and Google keys are NOT in the code. Keys live in
  GitHub Secrets (GitHub also masks them in logs); links live in your private Google Sheet.
- yt-dlp is silenced and error messages are never printed. Logs show only short anonymous
  codes like #a3f9c1, never a link.
- Forks and pull requests cannot read your secrets. The workflow does not run on pull requests.

## One-time setup

### 1. Google Sheet + add-link page
1. Create a new Google Sheet named Reel Queue. Copy its ID from the URL
   (docs.google.com/spreadsheets/d/THIS_PART/edit).
2. In the sheet: Extensions > Apps Script.
3. Put the contents of apps-script/Code.gs into Code.gs.
4. Add an HTML file named exactly `Index` and paste apps-script/Index.html.
5. Deploy > New deployment > Web app. Execute as: Me. Who has access: Only myself.
6. Open the Web app URL once (it creates the Queue and Failed tabs) and add it to your phone's home screen.

### 2. Drive folder
Pick the Drive folder. Its ID is the last part of the folder URL (drive.google.com/drive/folders/THIS_PART).
Use the same Google account as the keys below.

### 3. Google keys (lets the Action use your Drive + Sheet)
1. https://console.cloud.google.com : create a project.
2. APIs & Services > Library: enable Google Drive API and Google Sheets API.
3. Google Auth Platform: Get started (app name, email, External), then Branding, then publish
   the app (Audience > Publish app, status "In production"). In "Testing" status the key
   expires after 7 days.
4. Clients > Create client > Web application. Redirect URI: https://developers.google.com/oauthplayground
   Copy the Client ID and Client secret.
5. https://developers.google.com/oauthplayground : gear icon > Use your own OAuth credentials >
   paste both. Scopes (one line):
   https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets
   Authorize, then Exchange authorization code for tokens, and copy the Refresh token.
   Do this AFTER the app is published, otherwise the token expires after 7 days.

### 4. GitHub secrets
Repo > Settings > Secrets and variables > Actions > New repository secret:

| Name | Value |
|---|---|
| GOOGLE_CLIENT_ID | from step 3 |
| GOOGLE_CLIENT_SECRET | from step 3 |
| GOOGLE_REFRESH_TOKEN | from step 3 |
| DRIVE_FOLDER_ID | from step 2 (the ID only) |
| SHEET_ID | from step 1 (the ID only) |
| FB_COOKIES | optional, see below |

### 5. Start
Actions > Reel queue > Run workflow. It then keeps itself running.

## If the Google key expires
Symptom: the run turns red and the log says `error (RefreshError)`. Repeat step 3.5 and replace the
GOOGLE_REFRESH_TOKEN secret, then Run workflow.

## If many reels fail
Facebook sometimes blocks cloud servers. Fix: export cookies from a Facebook account
(browser extension "Get cookies.txt LOCALLY", Netscape format) and paste the whole file into the
FB_COOKIES secret. A spare account is safer than your main one. Private, deleted or friends-only
reels will keep failing; delete their rows from the Failed tab.

## Files
- .github/workflows/reel-queue.yml - the self-looping job and the hourly safety net
- reelbot/loop.py - the 10 minute loop
- reelbot/queue_logic.py - the queue/failed rules
- reelbot/downloader.py - yt-dlp, best quality, mp4, silenced
- reelbot/drive.py, reelbot/sheets_store.py - Google Drive and Sheet access
- apps-script/ - the add-link page (lives in your Google account, not run from GitHub)
- tests/ - python -m unittest discover tests

Use it only for content you are allowed to save.

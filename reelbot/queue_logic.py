"""Core queue rules. Pure logic, no Google or network code, so it is easy to test.

Rules (one run = one scheduled tick, every ~10 minutes):
  1. Always look at the main Queue first.
  2. A link that fails is moved to the END of the Failed list and the run
     immediately tries the next link (no waiting).
  3. If the Queue is empty, retry Failed links from the top. A Failed link that
     fails again goes back to the END of the Failed list. Each Failed link is
     tried at most once per run.
  4. After the first success the run ends. The next run starts ~10 minutes later.
  5. Before every attempt the Queue is checked again, so new links jump ahead
     of the Failed retries.

Nothing here prints a link: logs of a public repo are public.
"""
import hashlib
import time


def tag(link):
    """Short anonymous id for logs (never log the link itself)."""
    return hashlib.sha1(link.encode()).hexdigest()[:6]


def process(store, download, upload, log=print, deadline=None, clock=time.monotonic):
    """Returns 'success', 'idle', 'timeout' or 'upload_error'."""
    tried_failed = set()
    while True:
        if deadline is not None and clock() > deadline:
            log("Time budget used up, stopping until next run.")
            return "timeout"

        link = store.queue_head()
        source = "queue"
        if link is None:
            source = "failed"
            link = next((l for l in store.failed_list() if l not in tried_failed), None)
            if link is None:
                log("Nothing left to try. Waiting for next run.")
                return "idle"

        log(f"Trying {source} item #{tag(link)}")
        try:
            path = download(link)
        except Exception as exc:  # download problem -> link's fault
            log(f"Download failed for #{tag(link)}")
            store.failed_record(link, str(exc)[:300])
            if source == "queue":
                store.queue_remove(link)
            tried_failed.add(link)
            continue

        try:
            upload(path)
        except Exception as exc:  # Drive problem -> not the link's fault, keep it queued
            log(f"Upload to Drive failed ({type(exc).__name__}). Link kept in place.")
            return "upload_error"

        if source == "queue":
            store.queue_remove(link)
        else:
            store.failed_remove(link)
        log(f"Done #{tag(link)} -> Drive. Waiting for next run.")
        return "success"

"""Facebook reel download using yt-dlp (best quality video + audio, merged to mp4).

Privacy: yt-dlp is silenced completely. Its messages contain the reel link and
video id, and the logs of a public repo are public.
"""
import glob
import os

import yt_dlp


class _Silent:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def download_reel(link, out_dir, cookies_file=None):
    opts = {
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "format": "bv*+ba/b",  # best video + best audio, else best single file
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _Silent(),
        "retries": 3,
        "fragment_retries": 3,
        "restrictfilenames": True,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(link, download=True)

    path = None
    for item in info.get("requested_downloads") or []:
        if item.get("filepath"):
            path = item["filepath"]
    if not path or not os.path.exists(path):
        files = sorted(glob.glob(os.path.join(out_dir, "*.*")), key=os.path.getsize)
        path = files[-1] if files else None
    if not path or os.path.getsize(path) == 0:
        raise RuntimeError("No video file was produced")
    return path

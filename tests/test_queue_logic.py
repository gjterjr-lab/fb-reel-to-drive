import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from reelbot.queue_logic import process  # noqa: E402


class FakeStore:
    def __init__(self, queue=(), failed=()):
        self.queue = list(queue)
        self.failed = list(failed)
        self.errors = {}

    def queue_head(self):
        return self.queue[0] if self.queue else None

    def queue_remove(self, link):
        self.queue.remove(link)

    def failed_list(self):
        return list(self.failed)

    def failed_remove(self, link):
        self.failed.remove(link)

    def failed_record(self, link, error):
        if link in self.failed:
            self.failed.remove(link)
        self.failed.append(link)
        self.errors[link] = error


def run(store, bad=(), upload_fails=False):
    attempts, uploaded = [], []

    def download(link):
        attempts.append(link)
        if link in bad:
            raise RuntimeError("nope")
        return link

    def upload(path):
        if upload_fails:
            raise OSError("drive down")
        uploaded.append(path)

    result = process(store, download, upload, log=lambda m: None)
    return result, attempts, uploaded


class QueueLogic(unittest.TestCase):
    def test_success_takes_first_and_stops(self):
        s = FakeStore(queue=["a", "b"])
        result, attempts, up = run(s)
        self.assertEqual((result, attempts, up), ("success", ["a"], ["a"]))
        self.assertEqual(s.queue, ["b"])

    def test_failure_moves_to_failed_and_next_runs_immediately(self):
        s = FakeStore(queue=["a", "b", "c"])
        result, attempts, up = run(s, bad={"a"})
        self.assertEqual(result, "success")
        self.assertEqual(attempts, ["a", "b"])
        self.assertEqual(up, ["b"])
        self.assertEqual(s.queue, ["c"])
        self.assertEqual(s.failed, ["a"])

    def test_queue_new_links_before_failed(self):
        s = FakeStore(queue=["new"], failed=["old"])
        result, attempts, _ = run(s)
        self.assertEqual(attempts, ["new"])

    def test_failed_retried_when_queue_empty_and_rotated_to_end(self):
        s = FakeStore(failed=["f1", "f2", "f3"])
        result, attempts, up = run(s, bad={"f1", "f2"})
        self.assertEqual(result, "success")
        self.assertEqual(attempts, ["f1", "f2", "f3"])
        self.assertEqual(up, ["f3"])
        self.assertEqual(s.failed, ["f1", "f2"])  # f3 removed, others moved to end in order

    def test_each_failed_tried_once_per_run(self):
        s = FakeStore(failed=["f1", "f2"])
        result, attempts, _ = run(s, bad={"f1", "f2"})
        self.assertEqual(result, "idle")
        self.assertEqual(attempts, ["f1", "f2"])
        self.assertEqual(s.failed, ["f1", "f2"])

    def test_link_that_just_failed_not_retried_same_run(self):
        s = FakeStore(queue=["a"])
        result, attempts, _ = run(s, bad={"a"})
        self.assertEqual(result, "idle")
        self.assertEqual(attempts, ["a"])
        self.assertEqual(s.failed, ["a"])
        self.assertEqual(s.queue, [])

    def test_empty_everything_is_idle(self):
        self.assertEqual(run(FakeStore())[0], "idle")

    def test_upload_error_keeps_link_in_place(self):
        s = FakeStore(queue=["a", "b"])
        result, attempts, _ = run(s, upload_fails=True)
        self.assertEqual(result, "upload_error")
        self.assertEqual(s.queue, ["a", "b"])
        self.assertEqual(s.failed, [])


if __name__ == "__main__":
    unittest.main()

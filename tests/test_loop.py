import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from reelbot.loop import run_loop  # noqa: E402


class FakeTime:
    def __init__(self):
        self.t = 0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def go(results, loop_seconds=3000, **kw):
    ft = FakeTime()
    logs = []
    it = iter(results)

    def run_pass():
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    code = run_loop(run_pass, log=logs.append, sleep=ft.sleep, clock=ft.clock,
                    loop_seconds=loop_seconds, cycle_seconds=600, **kw)
    return code, ft, logs


class LoopTests(unittest.TestCase):
    def test_runs_until_budget_then_hands_over(self):
        code, ft, logs = go(["success", "idle", "idle", "success", "idle"])
        self.assertEqual(code, 0)
        self.assertEqual(ft.sleeps, [600, 600, 600, 600])  # 5 rounds, 4 waits
        self.assertIn("Round 5: idle", logs)

    def test_three_bad_rounds_in_a_row_stop_with_failure(self):
        code, ft, logs = go(["upload_error", RuntimeError("x"), "error"])
        self.assertEqual(code, 1)
        self.assertEqual(len(ft.sleeps), 2)

    def test_good_round_resets_bad_counter(self):
        code, ft, _ = go(["upload_error", "upload_error", "success", "upload_error", "idle"])
        self.assertEqual(code, 0)

    def test_exception_message_never_logged(self):
        code, ft, logs = go([ValueError("https://facebook.com/reel/SECRET123"), "idle", "idle", "idle", "idle"])
        self.assertTrue(all("SECRET123" not in l and "facebook" not in l for l in logs))
        self.assertIn("Round 1: error (ValueError)", logs)

    def test_timeout_round_is_not_a_failure(self):
        code, ft, _ = go(["timeout", "timeout", "timeout", "timeout", "timeout"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

"""The 10-minute loop. Pure logic (clock and sleep are injected) so it can be tested.

One GitHub job keeps running for about 5 hours 20 minutes. Each round it does
one pass over the queue, then waits 10 minutes. When its time is used up it
returns 0 and the workflow starts the next job. If several rounds in a row
fail it returns 1, so the job turns red (GitHub emails you) and the chain stops;
the hourly safety-net schedule starts a fresh loop later.

Logs never contain error messages, only the error type: messages can hold links.
"""
import time

BAD_RESULTS = ("error", "upload_error")


def run_loop(run_pass, log=print, sleep=time.sleep, clock=time.monotonic,
             loop_seconds=19200, cycle_seconds=600, max_bad=3):
    start = clock()
    n = 0
    bad = 0
    while True:
        n += 1
        try:
            result = run_pass()
        except Exception as exc:
            result = "error"
            log(f"Round {n}: error ({type(exc).__name__})")
        else:
            log(f"Round {n}: {result}")

        bad = bad + 1 if result in BAD_RESULTS else 0
        if bad >= max_bad:
            log("Too many failing rounds in a row. Stopping so the run turns red.")
            return 1
        if clock() - start + cycle_seconds >= loop_seconds:
            log("Loop time used up. Handing over to the next run.")
            return 0
        sleep(cycle_seconds)

"""Wait for asynchronous spend writes before measuring a new budget boundary."""

import time


def settled_info(fetch, *, stable_seconds=12, timeout=45):
    deadline = time.monotonic() + timeout
    unchanged_since = time.monotonic()
    previous = None
    while time.monotonic() < deadline:
        current = fetch()
        spend = current["spend"]
        if spend != previous:
            previous = spend
            unchanged_since = time.monotonic()
        elif time.monotonic() - unchanged_since >= stable_seconds:
            return current
        time.sleep(1)
    raise RuntimeError("Accounting did not settle before the budget probe")

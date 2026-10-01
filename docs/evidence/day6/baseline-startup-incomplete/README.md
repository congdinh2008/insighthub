# Incomplete startup run

Source101094a, unchanged dataset. 150 runtime records,120 passed,30 semantic failures. The first14cases failed with local HTTP disconnection while the newly started baseline port-forward was reconnecting. The preliminary health check incorrectly used /health instead of /readyz; its failed shell command did not stop the subsequent chain. No final or verifier ran. Raw Promptfoo JSON/HTML and result rows are retained. Restart only after bounded /readyz checks succeed consecutively; do not retry individual failed cases into this report.

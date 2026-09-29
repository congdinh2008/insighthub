"""Host-owned test allowlist; never supplied by model output."""

import math

from task import cost_usd

assert math.isclose(cost_usd(1000, 100, 500), 0.00041)
assert math.isclose(cost_usd(1000, 0, 1000), 0.0001)
assert cost_usd(0, 0, 0) == 0
for invalid in [(-1, 0, 0), (1, -1, 0), (1, 0, 2), (True, 0, 0), (1.5, 0, 0)]:
    try:
        cost_usd(*invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid usage accepted")
print("6 billing boundaries and cached-token arithmetic passed")

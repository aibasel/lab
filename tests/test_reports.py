from __future__ import division

from lab import reports


def test_gm():
    for numbers, mean in [([2, 8], 4), ([4, 1, 1 / 32], 0.5), ([0], 0)]:
        assert round(reports.gm(numbers), 2) == mean

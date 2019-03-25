from lab import reports


def test_geometric_mean():
    for numbers, mean in [([2, 8], 4), ([4, 1, 1 / 32.], 0.5), ([0], 0)]:
        assert round(reports.geometric_mean(numbers), 2) == mean

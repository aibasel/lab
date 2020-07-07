import pytest

from lab import reports, tools


@pytest.mark.parametrize(
    "numbers, mean", [([2, 8], 4), ([4, 1, 1 / 32.0], 0.5), ([0], 0)]
)
def test_geometric_mean(numbers, mean):
    assert round(reports.geometric_mean(numbers), 2) == mean


def geometric_mean_old(values):
    return tools.product(values) ** (1.0 / len(values))


@pytest.mark.parametrize(
    "values", [[1, 2, 4, 5], [0.4, 0.8], [2, 8], [10 ** (-5), 5000]]
)
def test_geometric_mean1(values):
    assert round(geometric_mean_old(values), 2) == round(
        reports.geometric_mean(values), 2
    )

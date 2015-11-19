from downward import cached_revision


def test_strip_options():
    for before, after in [
            (['foo'], ['foo']),
            (['foo', '-j4'], ['foo']),
            (['-j12', 'foo'], ['foo']),
            (['-j', '12', 'foo'], ['foo']),
            (['-j', '12x', 'foo'], ['12x', 'foo']),
            (['foo', '-j'], ['foo']),
            (['-j'], []),
            (['-j4'], []),
            (['-j', '4'], []),
            (['-j4', '4'], ['4']),
            ]:
        assert cached_revision._get_options_relevant_for_cache_name(
            before) == after

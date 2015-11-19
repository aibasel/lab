from downward import suites

def test_for_duplicates():
    for funcname in dir(suites):
        if not funcname.startswith('suite_'):
            continue
        print 'Test', funcname
        func = getattr(suites, funcname)
        domains = func()
        assert len(set(domains)) == len(domains)


def test_costs():
    partition = (
        suites.suite_unit_costs() + suites.suite_diverse_costs() +
        suites.suite_alternative_formulations())
    assert set(partition) == set(suites.suite_all())
    assert len(set(partition)) == len(partition)

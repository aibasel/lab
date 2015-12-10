from downward import suites

def test_for_duplicates():
    for funcname in dir(suites):
        if not funcname.startswith('suite_'):
            continue
        print 'Test', funcname
        func = getattr(suites, funcname)
        domains = func()
        assert len(set(domains)) == len(domains)

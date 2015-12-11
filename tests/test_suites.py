from collections import Counter

from downward import suites
from downward.suites import *


def test_for_duplicates():
    for funcname in dir(suites):
        if not funcname.startswith('suite_'):
            continue
        print 'Test', funcname
        func = getattr(suites, funcname)
        domains = func()
        assert domains == sorted(domains)
        assert len(set(domains)) == len(domains), Counter(domains)


def test_suite_satisficing():
    assert (
        set(suite_satisficing_adl() + suite_satisficing_strips()) ==
        set(suite_ipc98_to_ipc04() + suite_ipc06() +
            suite_ipc06_strips_compilations() + suite_ipc08_sat() +
            suite_ipc11_sat()))


def test_suite_optimal():
    assert (
        set(suite_optimal_adl() + suite_optimal_strips()) ==
        set(suite_ipc98_to_ipc04() + suite_ipc06() +
            suite_ipc06_strips_compilations() + suite_ipc08_opt() +
            suite_ipc11_opt()))

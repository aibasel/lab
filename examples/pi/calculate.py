#! /usr/bin/env python

import sys
import time

def calculate_pi(rounds):
    s = 0
    i = 1
    for _ in xrange(rounds):
        time.sleep(10**-4)
        s += 1./i - 1./(i+2)
        i += 4
    return 4 * s

if __name__ == '__main__':
    start = time.time()
    rounds = int(sys.argv[1]) if len(sys.argv) >= 2 else 1000
    print "Pi: %f" % calculate_pi(rounds)
    print "Time: %f" % (time.time() - start)

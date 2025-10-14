"""
Test CPU time limiting functionality for child processes.

These tests verify that the Call class correctly tracks and enforces
CPU time limits across process trees, including forked and spawned children.
"""

import contextlib
import os
import sys
import tempfile

import pytest

from lab.calls.call import Call


@pytest.fixture
def temp_script():
    """Fixture to create and cleanup temporary Python scripts."""
    scripts = []

    def _create_script(content):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            script_path = f.name
        scripts.append(script_path)
        return script_path

    yield _create_script

    # Cleanup
    for script in scripts:
        with contextlib.suppress(OSError):
            os.unlink(script)


def test_no_time_limit(temp_script):
    """Test that processes work normally without a time limit."""
    call = Call(
        [sys.executable, "-c", "print('Hello from test!')"],
        name="no-limit-test",
    )
    retcode = call.wait()
    assert retcode == 0, "Process should complete successfully without time limit"
    assert not call.cpu_time_limit_exceeded()


def test_single_process_cpu_limit(temp_script):
    """Test CPU limit enforcement for a single process via RLIMIT_CPU."""
    script = temp_script("""
import time
start = time.time()
# Busy loop for ~1.5 seconds of CPU time
while time.time() - start < 1.5:
    x = sum(range(1000000))
print("Done!")
""")

    call = Call(
        [sys.executable, script],
        name="single-process-test",
        time_limit=1,  # 1 second CPU limit
    )
    retcode = call.wait()

    # Process should be terminated by RLIMIT_CPU (SIGXCPU = signal 24)
    # Return code is negative signal number
    assert retcode != 0, "Process should be terminated by CPU limit"
    assert retcode < 0, "Process should be killed by signal"


def test_parent_and_child_processes(temp_script):
    """Test CPU limit enforcement for parent + spawned child processes."""
    script = temp_script("""
import subprocess
import sys
import time

# Create a child process that also uses CPU
child_script = '''
import time
start = time.time()
while time.time() - start < 1.2:
    x = sum(range(1000000))
'''

# Spawn a child process
proc = subprocess.Popen([sys.executable, '-c', child_script])

# Parent also uses some CPU
start = time.time()
while time.time() - start < 1.2:
    x = sum(range(1000000))

proc.wait()
print("Done!")
""")

    call = Call(
        [sys.executable, script],
        name="parent-child-test",
        time_limit=1,  # 1 second CPU limit (should be exceeded by parent+child ~2.4s)
    )
    retcode = call.wait()

    # The monitoring thread should detect combined CPU time exceeds limit
    assert (
        call.cpu_time_limit_exceeded()
    ), "CPU time limit should be exceeded for parent+child processes"
    assert retcode != 0, "Process should be terminated"


def test_nested_children_grandchildren(temp_script):
    """Test CPU limit enforcement across multiple process generations."""
    script = temp_script("""
import subprocess
import sys
import time

# Grandchild script inline
grandchild_code = 'import time; start = time.time(); x = 0\\n'
grandchild_code += 'while time.time() - start < 1: x = sum(range(1000000))'

# Child script that spawns grandchild
child_code = 'import subprocess, sys, time\\n'
child_code += 'gc = \\'import time; start = time.time()\\\\n\\'\\n'
child_code += 'gc += \\'while time.time() - start < 1: x = sum(range(1000000))\\'\\n'
child_code += 'proc = subprocess.Popen([sys.executable, \\"-c\\", gc])\\n'
child_code += 'start = time.time()\\n'
child_code += 'while time.time() - start < 0.7: x = sum(range(1000000))\\n'
child_code += 'proc.wait()'

# Parent spawns child
proc = subprocess.Popen([sys.executable, '-c', child_code])

# Parent also uses some CPU (0.7 second)
start = time.time()
while time.time() - start < 0.7:
    x = sum(range(1000000))

proc.wait()
print("Done!")
""")

    call = Call(
        [sys.executable, script],
        name="nested-children-test",
        time_limit=1,  # 1 second limit, but parent+child+grandchild = ~2.7 seconds
    )
    retcode = call.wait()

    # Should detect CPU time across entire process tree
    assert (
        call.cpu_time_limit_exceeded()
    ), "CPU time limit should be exceeded for multi-generational process tree"
    assert retcode != 0, "Process should be terminated"


def test_fork_and_spawn_mix(temp_script):
    """Test CPU limit with both forked and spawned child processes."""
    script = temp_script("""
import subprocess
import sys
import time
import os

# Script for spawned child
spawned_script = '''
import time
start = time.time()
# Uses 0.7 second of CPU
while time.time() - start < 0.7:
    x = sum(range(1000000))
'''

# Fork a child process
pid = os.fork()
if pid == 0:
    # Child process - do some CPU work
    start = time.time()
    while time.time() - start < 0.7:
        x = sum(range(1000000))
    os._exit(0)
else:
    # Parent process - spawn another child
    proc = subprocess.Popen([sys.executable, '-c', spawned_script])

    # Parent also uses CPU
    start = time.time()
    while time.time() - start < 1:
        x = sum(range(1000000))

    # Wait for both children
    os.waitpid(pid, 0)
    proc.wait()
    print("Done!")
""")

    call = Call(
        [sys.executable, script],
        name="fork-spawn-test",
        time_limit=1,  # 1 second limit, but total = ~2.4 seconds
    )
    retcode = call.wait()

    # Should track both forked and spawned children
    assert (
        call.cpu_time_limit_exceeded()
    ), "CPU time limit should be exceeded with fork+spawn mix"
    assert retcode != 0, "Process should be terminated"


def test_process_completes_within_limit(temp_script):
    """Test that processes completing within limit are not terminated."""
    script = temp_script("""
import time
start = time.time()
# Busy loop for ~0.3 seconds of CPU time
while time.time() - start < 0.3:
    x = sum(range(1000000))
print("Done!")
""")

    call = Call(
        [sys.executable, script],
        name="within-limit-test",
        time_limit=2,  # 2 second CPU limit (plenty of room)
    )
    retcode = call.wait()

    # Process should complete normally
    assert retcode == 0, "Process should complete successfully within limit"
    assert not call.cpu_time_limit_exceeded(), "CPU time limit should not be exceeded"


def test_short_lived_child_cpu_time_captured(temp_script):
    """
    Test that CPU time from short-lived children is captured even if they
    terminate before the final measurement.

    This test creates a scenario where:
    - A child starts and uses CPU time for ~1 second (long enough to be sampled)
    - The child terminates while parent is still running
    - Parent continues for another ~1 second after child dies
    - We verify that the child's CPU time is still counted in final total
    """
    script = temp_script("""
import subprocess
import sys
import time

# Child that uses ~1s of CPU and terminates
child_script = '''
import time
start = time.time()
while time.time() - start < 1:
    x = sum(range(1000000))
print("Child done")
'''

# Start child process
proc = subprocess.Popen([sys.executable, '-c', child_script])

# Parent also uses CPU time for ~0.5 second while child is running
start = time.time()
while time.time() - start < 0.5:
    x = sum(range(1000000))

# Wait for child to complete
proc.wait()

# Parent continues using CPU time for another ~0.5 second after child terminates
# This ensures the final measurement happens after child is gone
start = time.time()
while time.time() - start < 0.5:
    x = sum(range(1000000))

print("Parent done")
""")

    call = Call(
        [sys.executable, script],
        name="short-lived-child-test",
        time_limit=5,  # High limit to avoid termination
    )
    retcode = call.wait()

    assert retcode == 0, "Process should complete successfully"
    assert not call.cpu_time_limit_exceeded(), "Should not exceed limit"

    # The key assertion: we should have captured the child's ~1s + parent's ~1s
    # = ~2s total even though the child terminated before the final measurement.
    # We use >= 1.4 to account for slight timing variations.
    assert call.cpu_time is not None, "Should have CPU time measurement"
    assert call.cpu_time >= 1.4, (
        f"Should capture parent + child CPU time (>= 1.4s), but got "
        f"{call.cpu_time:.2f}s. This indicates terminated child's CPU time was "
        f"not properly captured."
    )


def test_sequential_children_cpu_time_accumulated(temp_script):
    """
    Test that CPU time from sequential children is properly accumulated.

    This is a regression test for a critical bug where sequential children's
    CPU times would be lost. The scenario:
    - Child1 spawns, uses 1s of CPU, terminates
    - Child2 spawns, uses 0.5s of CPU, terminates
    - With correct "per-PID accumulation", 1.5s is reported (1s + 0.5s)
    """
    script = temp_script("""
import subprocess
import sys
import time

# First child: uses ~1s of CPU then terminates
child1_script = '''
import time
start = time.time()
while time.time() - start < 1:
    x = sum(range(1000000))
print("Child1 done")
'''

# Second child: uses ~0.5s of CPU then terminates
child2_script = '''
import time
start = time.time()
while time.time() - start < 0.5:
    x = sum(range(1000000))
print("Child2 done")
'''

# Run child1, wait for completion
proc1 = subprocess.Popen([sys.executable, '-c', child1_script])
proc1.wait()

# Small sleep to ensure monitoring thread sees child1 disappeared
time.sleep(0.5)

# Run child2, wait for completion
proc2 = subprocess.Popen([sys.executable, '-c', child2_script])
proc2.wait()

print("Parent done")
""")

    call = Call(
        [sys.executable, script],
        name="sequential-children-test",
        time_limit=5,  # High limit to avoid termination
    )
    retcode = call.wait()

    assert retcode == 0, "Process should complete successfully"
    assert not call.cpu_time_limit_exceeded(), "Should not exceed limit"

    # Critical assertion: total should be ~1.5s (child1 + child2). We use >= 1.2
    # to account for timing variations while ensuring both children are counted.
    assert call.cpu_time is not None, "Should have CPU time measurement"
    assert call.cpu_time >= 1.2, (
        f"Should accumulate sequential children's CPU time (~1s + ~0.5s = ~1.5s), "
        f"but got {call.cpu_time:.2f}s."
    )

"""
Test that configuring logging does not create duplicate handlers.

tools.configure_logging() is called when lab is imported and again whenever an
Experiment is constructed. It must be idempotent: each call has to reset the
root logger to exactly one stdout handler and one stderr handler, so that log
messages are not emitted multiple times.
"""

import logging

import lab  # noqa: F401  (importing lab configures logging)
from lab import tools


def test_no_duplicate_handlers():
    root_logger = logging.getLogger("")
    for _ in range(3):
        tools.configure_logging()
        assert len(root_logger.handlers) == 2

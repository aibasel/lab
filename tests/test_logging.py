"""
Test that lab configures logging when it runs, so that logging.critical()
aborts the program.

Lab relies on logging.critical() to report fatal errors and stop execution.
This only works if the custom logging handler installed by
tools.configure_logging() is active. The handler is installed when an
Experiment is constructed and also when reports and fetchers run, so that
critical errors abort the program even when no Experiment exists (e.g., when
generating a report directly).
"""

import logging

import pytest

import lab.experiment  # noqa: F401  (import first to avoid a circular import)
from lab import tools
from lab.fetcher import Fetcher


def test_configure_logging_is_idempotent():
    # configure_logging() is called from several entry points, so calling it
    # repeatedly must not accumulate duplicate handlers.
    root_logger = logging.getLogger("")
    for _ in range(3):
        tools.configure_logging()
        assert len(root_logger.handlers) == 2


def test_fetcher_aborts_without_experiment():
    # Drop any configured handlers to simulate using lab without constructing
    # an Experiment. Running the fetcher must reinstall the abort handler so
    # that logging.critical() (here: missing source dir) exits the program.
    root_logger = logging.getLogger("")
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    with pytest.raises(SystemExit):
        Fetcher()("/does/not/exist")

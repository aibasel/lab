from lab import tools

#: Lab version number. A "+" is appended to all non-tagged revisions.
__version__ = "8.9+"

# Configure logging as soon as Lab is imported. This ensures that
# logging.critical() aborts the program regardless of how Lab is used, e.g.,
# when generating reports without constructing an Experiment.
tools.configure_logging()

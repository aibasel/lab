Install Lab
-----------

Lab requires Linux and we recommend using `uv <https://docs.astral.sh/uv/>`_. ::

    # Create a uv project in the current directory.
    uv init --bare --no-workspace --pin-python

    # Install Lab.
    uv add lab

    # Add uv files to version control.
    git add pyproject.toml .python-version uv.lock

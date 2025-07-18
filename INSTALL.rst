Install Lab
-----------

Lab requires Python 3 and Linux (e.g., Ubuntu). ::

    # Install uv.
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Create a uv project in the current directory.
    uv init --bare --no-workspace --pin-python

    # Install Lab.
    uv add lab

    # Add uv files to version control.
    git add pyproject.toml .python-version uv.lock

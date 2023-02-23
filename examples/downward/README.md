# Setup instructions

Create a [virtual environment](https://docs.python.org/3/tutorial/venv.html),
activate it and install all dependencies:

    sudo apt install python3 python3-venv
    python3 -m venv --prompt myvenv .venv
    source .venv/bin/activate
    pip install --upgrade pip wheel
    pip install -r requirements.txt

If the last step fails, try regenerating a new `requirements.txt` from
`requirements.in` for your Python version:

    source .venv/bin/activate
    pip install pip-tools
    pip-compile
    pip install -r requirements.txt

Please note that before running an experiment script you need to
activate the virtual environment with

    source .venv/bin/activate

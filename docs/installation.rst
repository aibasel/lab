Installation
============

For the sake of illustration we install everything in the ``~/workshop``
directory.

lab + downward
--------------
::

    sudo apt-get install mercurial python2.7 python-matplotlib
    mkdir ~/workshop
    cd ~/workshop
    hg clone https://bitbucket.org/jendrikseipp/lab

Append to your ``.bashrc``::

    LAB=~/workshop/lab
    if [ -z "$PYTHONPATH" ]; then
        export PYTHONPATH=${LAB}
    else
        export PYTHONPATH=${PYTHONPATH}:${LAB}
    fi

Check that everything works::

    source ~/.bashrc
    cd ~/workshop/lab/examples/pi
    ./pi.py --help
    ./pi.py build

Fast Downward planning system
-----------------------------
::

    sudo apt-get install mercurial g++ make python flex bison gawk
    sudo apt-get install g++-multilib  # 64-bit
    cd ~/workshop
    hg clone http://hg.fast-downward.org fast-downward
    cd ~/workshop/fast-downward/src
    ./build_all

Build ``downward`` experiment::

    cd ~/workshop/lab/examples/planner
    ./planner.py
    ./planner.py 1 2 3 4

# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import colorsys
import email.mime.text
import functools
import json
import logging
import os
import platform
import re
import shutil
import smtplib
import subprocess
import sys
import traceback

from external import argparse


LOG_LEVEL = None

# Directories and files

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
USER_DIR = os.path.join(os.path.expanduser('~'), 'lab')

RUNNING_ON_GRID = platform.node().startswith('gkigrid')


class ErrorAbortHandler(logging.StreamHandler):
    """
    Custom logging Handler that exits when a critical error is encountered.
    """
    def emit(self, record):
        logging.StreamHandler.emit(self, record)
        if record.levelno >= logging.CRITICAL:
            sys.exit('aborting')


def setup_logging(level):
    # Python adds a default handler if some log is written before now
    # Remove all handlers that have been added automatically
    root_logger = logging.getLogger('')
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # Handler which writes LOG_LEVEL messages or higher to stdout
    console = ErrorAbortHandler(sys.stdout)
    # set a format which is simpler for console use
    format = '%(asctime)-s %(levelname)-8s %(message)s'
    formatter = logging.Formatter(format)
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    root_logger.addHandler(console)
    root_logger.setLevel(level)


def remove_none_values(func):
    """
    Remove all None values from the input list and call the original function.
    """
    @functools.wraps(func)
    def new_func(values):
        values = [val for val in values if val is not None]
        if not values:
            return None
        return round(func(values), 4)
    return new_func


def shell_escape(s):
    if s and s[0].isdigit():
        s = 'N' + s
    return s.upper().replace('-', '_').replace(' ', '_').replace('.', '_')


def uniq(iterable):
    result = []
    for x in iterable:
        if x not in result:
            result.append(x)
    return result


def divide_list(seq, size):
    """
    >>> divide_list(range(10), 4)
    [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]
    """
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def makedirs(dir):
    """
    makedirs variant that does not complain when the dir already exists
    """
    try:
        os.makedirs(dir)
    except OSError:
        # directory probably exists
        pass


def confirm(question):
    if RUNNING_ON_GRID:
        print question
        print 'Running on the grid -> We better stop here.'
        sys.exit('Aborted')
    answer = raw_input('%s (Y/N): ' % question).upper().strip()
    if not answer == 'Y':
        sys.exit('Aborted')


def overwrite_dir(path, overwrite=False):
    if os.path.exists(path):
        logging.info('The directory "%s" already exists.' % path)
        if not overwrite:
            confirm('Do you want to overwrite the existing directory?')
        shutil.rmtree(path)
    # We use the os.makedirs method instead of our own here to check if the dir
    # has really been properly deleted.
    os.makedirs(path)


def remove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


def natural_sort(alist):
    """Sort alist alphabetically, but special-case numbers to get
    file2.txt before file10.txt.

    >>> natural_sort(['file10.txt', 'file2.txt'])
    ['file2.txt', 'file10.txt']
    """
    def to_int_if_number(text):
        if text.isdigit():
            return int(text)
        else:
            return text.lower()

    def extract_numbers(text):
        parts = re.split("([0-9]+)", text)
        return map(to_int_if_number, parts)

    return sorted(alist, key=extract_numbers)


def find_file(filenames, dir='.'):
    for filename in filenames:
        path = os.path.join(dir, filename)
        if os.path.exists(path):
            return path
    raise IOError('none found in %r: %r' % (dir, filenames))


def import_python_file(filename, dirs=None):
    dirs = dirs or []
    parent_dir = os.path.dirname(filename)
    dirs.append(parent_dir)
    for dir in dirs:
        if dir not in sys.path:
            sys.path.insert(0, dir)
    filename = os.path.normpath(filename)
    filename = os.path.basename(filename)
    if filename.endswith('.py'):
        module_name = filename[:-3]
    elif filename.endswith('.pyc'):
        module_name = filename[:-4]
    else:
        module_name = filename

    # Reload already loaded modules to actually get the changes.
    if module_name in sys.modules:
        return reload(sys.modules[module_name])

    try:
        module = __import__(module_name)
        return module
    except ImportError as err:
        print traceback.format_exc()
        logging.critical('File "%s" could not be imported: %s' % (filename, err))


def _log_command(cmd, kwargs):
    assert isinstance(cmd, list)
    # Do not show complete env variables, only show PYTHONPATH
    kwargs_clean = kwargs.copy()
    env = kwargs_clean.get('env')
    if env:
        pythonpath = env.get('PYTHONPATH')
        if pythonpath:
            kwargs_clean['env'] = {'PYTHONPATH': pythonpath, '...': '...'}
    logging.info('Running command: %s %s' % (' '.join(cmd), kwargs_clean))


def run_command(cmd, **kwargs):
    """Run command cmd and return the output."""
    _log_command(cmd, kwargs)
    return subprocess.call(cmd, **kwargs)


def get_command_output(cmd, quiet=False, **kwargs):
    if not quiet:
        _log_command(cmd, kwargs)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, **kwargs)
    stdout, _ = p.communicate()
    return stdout.strip()


class Properties(dict):
    def __init__(self, filename=None):
        self.filename = filename
        self.load(filename)
        dict.__init__(self)

    def __str__(self):
        return json.dumps(self, indent=2)

    def load(self, filename):
        if not filename or not os.path.exists(filename):
            return
        with open(filename) as f:
            try:
                self.update(json.load(f))
            except ValueError as e:
                logging.critical("JSON parse error in file '%s': %s" % (filename, e))

    def write(self):
        """Write the properties to disk.

        The default implementation writes each item of a list on its own line
        making the file very long. Unfortunately this cannot be fixed by
        subclassing JSONEncoder, because the encode() method is only called once
        for the properties dict.
        """
        assert self.filename
        with open(self.filename, 'w') as f:
            json.dump(self, f, indent=2)


def fast_updatetree(src, dst, symlinks=False, ignore=None):
    """
    Copies the contents from src onto the tree at dst, overwrites files with
    the same name.

    Code taken and expanded from python docs.
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    makedirs(dst)

    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                if not os.path.isabs(linkto):
                    # Calculate new relative link path.
                    abs_link = os.path.abspath(os.path.join(os.path.dirname(srcname),
                                                            linkto))
                    linkto = os.path.relpath(abs_link, os.path.dirname(dstname))
                if os.path.exists(dstname):
                    remove(dstname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                fast_updatetree(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Exception, err:
            errors.append(err.args[0])
    if errors:
        raise Exception(errors)


def copy(src, dest, required=True, ignores=None):
    """
    Copies a file or directory to another file or directory
    """
    if os.path.isfile(src) and os.path.isdir(dest):
        makedirs(dest)
        dest = os.path.join(dest, os.path.basename(src))
        shutil.copy2(src, dest)
    elif os.path.isfile(src):
        makedirs(os.path.dirname(dest))
        shutil.copy2(src, dest)
    elif os.path.isdir(src):
        if ignores:
            fast_updatetree(src, dest, ignore=shutil.ignore_patterns(*ignores))
        else:
            fast_updatetree(src, dest)
    elif required:
        logging.critical('Required path %s cannot be copied to %s' %
                         (os.path.abspath(src), os.path.abspath(dest)))
    else:
        # Do not warn if an optional file cannot be copied.
        return


def sendmail(from_, to, subject, text, smtp_host='localhost', port=25):
    """Send an e-mail.

    *from_* is the sender's email address.
    *to* is the recipient's email address. ::

        Step('mail', sendmail, 'john@xyz.com', 'jane@xyz.com', 'Hi!', 'Howdy!')

    """
    # Create a text/plain message
    msg = email.mime.text.MIMEText(text)

    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(smtp_host, port)
    s.sendmail(from_, [to], msg.as_string())
    s.quit()


def get_color(fraction, min_wins):
    assert 0 <= fraction <= 1
    if min_wins:
        fraction = 1 - fraction

    # Calculate hues.
    start = colorsys.rgb_to_hsv(0, 0, 0.8)[0]
    end = colorsys.rgb_to_hsv(0, 0.8, 0)[0]

    return colorsys.hsv_to_rgb(start + fraction * (end - start), 1, 0.7)


def get_colors(values, min_wins):
    default = (0.5,) * 3
    real_values = [val for val in values if val is not None]
    if not real_values:
        return [default for val in values]
    min_value = min(real_values)
    max_value = max(real_values)
    diff = float(max_value - min_value)
    if diff == 0:
        if len(real_values) == len(values):
            # No value is None and they are all equal.
            return [default for val in values]
        else:
            # Some values are None, the rest are all equal.
            return [default if val is None else get_color(0, True) for val in values]
    colors = []
    for val in values:
        if val is None:
            colors.append(default)
        else:
            fraction = (val - min_value) / diff
            colors.append(get_color(fraction, min_wins))
    return colors


def rgb_fractions_to_html_color(r, g, b):
    return 'rgb(%d,%d,%d)' % (r * 255, g * 255, b * 255)


def get_terminal_size():
    import struct
    try:
        import fcntl
        import termios
    except ImportError:
        return (None, None)

    try:
        data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, 4 * '00')
        height, width = struct.unpack('4H', data)[:2]
        return (width, height)
    except Exception:
        return (None, None)


class RawAndDefaultsHelpFormatter(argparse.HelpFormatter):
    """
    Help message formatter which retains any formatting in descriptions and adds
    default values to argument help.
    """
    def __init__(self, prog, **kwargs):
        # Use the whole terminal width
        width, height = get_terminal_size()
        argparse.HelpFormatter.__init__(self, prog, width=width, **kwargs)

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help and not 'default' in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help

    def _format_args(self, action, default_metavar):
        """
        We want to show "[environment-specific options]" instead of "...".
        """
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs == argparse.PARSER:
            return '%s [environment-specific options]' % get_metavar(1)
        else:
            return argparse.HelpFormatter._format_args(self, action, default_metavar)


class ArgParser(argparse.ArgumentParser):
    def __init__(self, add_log_option=True, *args, **kwargs):
        argparse.ArgumentParser.__init__(self, *args,
                                formatter_class=RawAndDefaultsHelpFormatter,
                                **kwargs)
        if add_log_option:
            try:
                self.add_argument('-l', '--log-level', dest='log_level',
                                  choices=['DEBUG', 'INFO', 'WARNING'],
                                  default='INFO')
            except argparse.ArgumentError:
                # The option may have already been added by a parent
                pass

    def parse_known_args(self, *args, **kwargs):
        args, remaining = argparse.ArgumentParser.parse_known_args(self, *args,
                                                                   **kwargs)

        global LOG_LEVEL
        # Set log level only once (May have already been deleted from sys.argv)
        if getattr(args, 'log_level', None) and not LOG_LEVEL:
            LOG_LEVEL = getattr(logging, args.log_level.upper())
            setup_logging(LOG_LEVEL)

        return (args, remaining)

    def directory(self, string):
        if not os.path.isdir(string):
            msg = '%r is not an evaluation directory' % string
            raise argparse.ArgumentTypeError(msg)
        return string


# Parse the log-level and set it
ArgParser(add_help=False).parse_known_args()

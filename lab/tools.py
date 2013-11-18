# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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
import logging
from numbers import Number
import os
import re
import shutil
import smtplib
import subprocess
import sys
import traceback

# Use simplejson where it's available, because it is compatible (just separately
# maintained), puts no blanks at line endings and loads json much faster:
# json_dump: 44.41, simplejson_dump: 45.90
# json_load: 7.32, simplejson_load: 2.92
# We cannot use cjson or ujson for the dumping, because the resulting files are
# very hard to read (cjson_dump: 5.78, ujson_dump: 2.44). Using ujson for
# loading might be feasible, but it would only result in a very small speed gain
# (ujson_load: 2.49). cjson loads even slower than simplejson (cjson_load: 3.28).
try:
    import simplejson as json
    assert json  # Silence pyflakes
except ImportError:
    import json

from external import argparse


LOG_LEVEL = None

# Directories and files

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
# TODO(v2.0): Use freedesktop specification.
DEFAULT_USER_DIR = os.path.join(os.path.expanduser('~'), 'lab')


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


def make_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


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
    answer = raw_input('%s (y/N): ' % question).strip()
    if not answer.lower() == 'y':
        sys.exit('Aborted')
    return True


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
    filename = os.path.abspath(filename)
    original_filename = filename
    dirs = dirs or []
    parent_dir = os.path.dirname(filename)
    dirs.append(parent_dir)
    sys.path = dirs + sys.path
    filename = os.path.basename(filename)
    if filename.endswith('.py'):
        module_name = filename[:-3]
    elif filename.endswith('.pyc'):
        module_name = filename[:-4]
    else:
        module_name = filename

    # Reload already loaded modules to actually get the changes.
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        module = __import__(module_name)
    except ImportError as err:
        print traceback.format_exc()
        logging.critical('File "%s" could not be imported: %s' % (original_filename, err))
    else:
        return module
    finally:
        for dir in dirs:
            sys.path.remove(dir)


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
        return json.dumps(self, indent=2, separators=(',', ': '))

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
            f.write(str(self))


class RunFilter(object):
    def __init__(self, filter, **kwargs):
        filter = filter or []
        self.filters = make_list(filter)
        for arg_name, arg_value in kwargs.items():
            if not arg_name.startswith('filter_'):
                logging.critical('Invalid keyword argument name "%s"' % arg_name)
            filter_for = arg_name[len('filter_'):]
            # Add a filter for the specified property.
            self.filters.append(self._build_filter(filter_for, arg_value))

    def _build_filter(self, prop, value):
        # Do not define this function inplace to force early binding. See:
        # stackoverflow.com/questions/3107231/currying-functions-in-python-in-a-loop
        def property_filter(run):
            # Do not use Collections.Iterable here to avoid strings being converted to a
            # list, e.g. filter_config_nick='astar' --> ['a', 's', 't', 'a', 'r']
            if isinstance(value, (list, tuple, set)):
                return run.get(prop) in value
            else:
                return run.get(prop) == value
        return property_filter

    def apply_to_run(self, run):
        # No need to copy the run as the original run is only needed if all
        # filters return True. In this case modified_run is never changed.
        modified_run = run
        for filter in self.filters:
            result = filter(modified_run)
            if not isinstance(result, (dict, bool)):
                logging.critical('Filters must return a dictionary or boolean')
            # If a dict is returned, use it as the new run,
            # else take the old one.
            if isinstance(result, dict):
                modified_run = result
            if not result:
                # Discard runs that returned False or an empty dictionary.
                return False
        return modified_run

    def apply(self, props):
        if not self.filters:
            return props
        new_props = Properties()
        for run_id, run in props.items():
            modified_run = self.apply_to_run(run)
            if modified_run:
                new_props[run_id] = modified_run
        new_props.filename = props.filename
        return new_props


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
        # If dstname is a symbolic link, remove it before trying to override it.
        # Without this shutil.copy2 cannot override broken symbolic links and
        # it will override the file that the link points to if the link is valid.
        if os.path.islink(dstname):
            remove(dstname)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                if not os.path.isabs(linkto):
                    # Calculate new relative link path.
                    abs_link = os.path.abspath(os.path.join(os.path.dirname(srcname),
                                                            linkto))
                    linkto = os.path.relpath(abs_link, os.path.dirname(dstname))
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
    assert 0 <= fraction <= 1, fraction
    if min_wins:
        fraction = 1 - fraction

    # Calculate hues.
    start = colorsys.rgb_to_hsv(0, 0, 0.8)[0]
    end = colorsys.rgb_to_hsv(0, 0.8, 0)[0]

    return colorsys.hsv_to_rgb(start + fraction * (end - start), 1, 0.7)


def get_colors(cells, min_wins):
    result = dict((col, (0.5, 0.5, 0.5)) for col in cells.keys())
    min_value, max_value = get_min_max(cells.values())

    if min_value == max_value:
        if min_value is None or None not in cells.values():
            # Either there are no float values in this row or
            # all values are floats (no value is None) and they are all equal.
            return result
        else:
            # Some values are None, the rest are all equal. The latter have
            # a distance of 0 to the min_value, so setting min_wins to True
            # highlights them all as the best values in this row.
            min_wins = True

    # If we land here, both min_value and max_value are not None.
    diff = float(max_value - min_value)

    for col, val in cells.items():
        if val is not None:
            val = round(val, 2)
            if diff == 0:
                assert val - min_value == 0, (val, min_value)
                fraction = 0
            else:
                fraction = (val - min_value) / diff
            result[col] = get_color(fraction, min_wins)
    return result


def get_min_max(items):
    """Returns min and max of all values in *items* that are not None.

    Floats are rounded to two decimal places. If no maximum and minimum is
    defined (e.g. all values None) None is returned for both min and max.
    """
    numbers = [round(val, 2) for val in items if isinstance(val, Number)]
    if numbers:
        return min(numbers), max(numbers)
    else:
        return None, None


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

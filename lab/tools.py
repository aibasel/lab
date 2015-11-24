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

import argparse
import colorsys
import functools
import logging
import os
import re
import shutil
import subprocess
import sys
import traceback

# Use simplejson where it's available, because it is compatible (just separately
# maintained), puts no blanks at line endings and loads json much faster:
# json_dump: 44.41s, simplejson_dump: 45.90s
# json_load: 7.32s, simplejson_load: 2.92s
# We cannot use cjson or ujson for dumping, because the resulting files are
# hard to read for humans (cjson_dump: 5.78, ujson_dump: 2.44). Using ujson for
# loading might be feasible, but it would only result in a very small speed gain
# (ujson_load: 2.49). cjson loads even slower than simplejson (cjson_load: 3.28).
try:
    import simplejson as json
except ImportError:
    import json


# TODO(v2.0): Use freedesktop specification.
DEFAULT_USER_DIR = os.path.join(os.path.expanduser('~'), 'lab')
LOG_LEVEL = None


def get_script_path():
    """Get absolute path to main script."""
    return os.path.abspath(sys.argv[0])


def get_script_dir():
    """Get absolute path to directory of main script."""
    return os.path.dirname(get_script_path())


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


def show_deprecation_warning(msg):
    logging.warning(msg)


class deprecated(object):
    """Decorator for marking deprecated functions or classes.

    The *msg* argument is optional, but the decorator always has to be
    called with brackets.
    """
    def __init__(self, msg=''):
        self.msg = msg

    def __call__(self, func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            msg = self.msg or '%s is deprecated.' % (func.__name__)
            show_deprecation_warning(msg)
            return func(*args, **kwargs)
        return new_func


def remove_none_values(func):
    """
    Remove all None values from the input list and call the original function.
    """
    @functools.wraps(func)
    def new_func(values):
        values = [val for val in values if val is not None]
        if not values:
            return None
        return func(values)
    return new_func


def make_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


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


def remove_path(path):
    if os.path.isfile(path):
        os.remove(path)
    else:
        shutil.rmtree(path)


def touch(filename):
    with open(filename, 'a'):
        os.utime(filename, None)


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


def _get_module_name(filename):
    basename = os.path.basename(filename)
    if basename.endswith('.py'):
        return basename[:-3]
    elif basename.endswith('.pyc'):
        return basename[:-4]
    else:
        return basename


def import_python_file(filename):
    filename = os.path.abspath(filename)
    original_sys_path = sys.path[:]
    sys.path = [os.path.dirname(filename)] + sys.path
    module_name = _get_module_name(filename)

    # If we have already loaded a file with the same basename, we need
    # to delete the cached module before loading the new one.
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        module = __import__(module_name)
    except ImportError as err:
        print traceback.format_exc()
        logging.critical('File "%s" could not be imported: %s' % (filename, err))
    else:
        return module
    finally:
        sys.path = original_sys_path


def _log_command(cmd, kwargs):
    assert isinstance(cmd, list)
    logging.info('Running command: %s %s' % (' '.join(cmd), kwargs))


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
        return json.dumps(self, indent=2, separators=(',', ': '), sort_keys=True)

    def load(self, filename):
        if not filename or not os.path.exists(filename):
            return
        with open(filename) as f:
            try:
                self.update(json.load(f))
            except ValueError as e:
                logging.critical("JSON parse error in file '%s': %s" % (filename, e))

    def write(self):
        """Write the properties to disk."""
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
            attribute = arg_name[len('filter_'):]
            # Add a filter for the specified property.
            self.filters.append(self._build_filter(attribute, arg_value))

    def _build_filter(self, prop, value):
        # Do not define this function inplace to force early binding.
        def property_filter(run):
            # We cannot use collections.Iterable here since we don't want
            # membership testing for str.
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
            # otherwise take the old one.
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

    Code taken and adapted from python docs.
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
            os.remove(dstname)
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
        ignore = shutil.ignore_patterns(*ignores) if ignores else None
        fast_updatetree(src, dest, ignore=ignore)
    elif required:
        logging.critical('Required path %s cannot be copied to %s' %
                         (os.path.abspath(src), os.path.abspath(dest)))
    else:
        # Do not warn if an optional file cannot be copied.
        return


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
            if diff == 0:
                fraction = 0
            else:
                fraction = (val - min_value) / diff
            result[col] = get_color(fraction, min_wins)
    return result


def get_min_max(items):
    """Return min and max of all values in *items* that are not None.

    If no maximum and minimum is defined (i.e., when all values are
    None), return (None, None).

    """
    numbers = [val for val in items if val is not None]
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
    Help message formatter which preserves the description format and adds
    default values to argument help messages.
    """
    def __init__(self, prog, **kwargs):
        # Use the whole terminal width.
        width, _ = get_terminal_size()
        argparse.HelpFormatter.__init__(self, prog, width=width, **kwargs)

    def _fill_text(self, text, width, indent):
        return '\n'.join([indent + line for line in text.splitlines()])

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help and 'default' not in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


def get_parser(add_log_option=True, **kwargs):
    kwargs.setdefault('formatter_class', RawAndDefaultsHelpFormatter)
    parser = argparse.ArgumentParser(**kwargs)
    if add_log_option:
        parser.add_argument(
            '-l', '--log-level',
            dest='log_level',
            choices=['DEBUG', 'INFO', 'WARNING'],
            default='INFO',
            help='Logging verbosity')
    return parser


def parse_and_set_log_level():
    # Set log level only once.
    global LOG_LEVEL
    if LOG_LEVEL:
        return

    parser = get_parser(add_help=False)
    args, remaining = parser.parse_known_args()

    if getattr(args, 'log_level', None):
        LOG_LEVEL = getattr(logging, args.log_level.upper())
        setup_logging(LOG_LEVEL)


parse_and_set_log_level()

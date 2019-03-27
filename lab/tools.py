# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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
import pkgutil
import re
import shutil
import subprocess
import sys

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

try:
    # Python 2
    user_input = raw_input
except NameError:
    # Python 3
    user_input = input


try:
    # Python 2
    string_type = basestring
except NameError:
    # Python 3
    string_type = str


def get_string(s):
    if isinstance(s, str):
        # Byte string in Python 2 or unicode string in Python 3.
        return s
    elif isinstance(s, bytes):
        # Bytes object in Python 3 (if-case handles Python 2 byte strings).
        return s.decode('utf-8')
    else:
        # Unicode string in Python 2.
        return s


def get_bytes(s):
    if isinstance(s, bytes):
        # Byte string in Python 2 or bytes object in Python 3.
        return s
    else:
        # Unicode string in Python 2 or 3 (if-case handles Python 2 byte strings).
        return s.encode('utf-8')


def get_script_path():
    """Get absolute path to main script."""
    return os.path.abspath(sys.argv[0])


def get_lab_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def configure_logging(level=logging.INFO):
    # Python adds a default handler if some log is written before this
    # function is called. We therefore remove all handlers that have
    # been added automatically.
    root_logger = logging.getLogger('')
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    class ErrorAbortHandler(logging.StreamHandler):
        """
        Logging handler that exits when a critical error is encountered.
        """
        def emit(self, record):
            logging.StreamHandler.emit(self, record)
            if record.levelno >= logging.CRITICAL:
                sys.exit('aborting')

    class StdoutFilter(logging.Filter):
        def filter(self, record):
            return record.levelno <= logging.WARNING

    class StderrFilter(logging.Filter):
        def filter(self, record):
            return record.levelno > logging.WARNING

    formatter = logging.Formatter('%(asctime)-s %(levelname)-8s %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(StdoutFilter())

    stderr_handler = ErrorAbortHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(StderrFilter())

    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)
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


def make_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def makedirs(path):
    """
    os.makedirs() variant that doesn't complain if the path already exists.
    """
    try:
        os.makedirs(path)
    except OSError:
        # Directory probably already exists.
        pass


def confirm_or_abort(question):
    answer = user_input('%s (y/N): ' % question).strip()
    if not answer.lower() == 'y':
        sys.exit('Aborted')


def confirm_overwrite_or_abort(path):
    confirm_or_abort(
        'The path "%s" already exists. Do you want to overwrite it?' % path)


def remove_path(path):
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
    else:
        shutil.rmtree(path)


def write_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)


def fill_template(template_name, **parameters):
    template = get_string(pkgutil.get_data(
        'lab', os.path.join('data', template_name + '.template')))
    return template % parameters


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
        return [to_int_if_number(part) for part in parts]

    return sorted(alist, key=extract_numbers)


def find_file(filenames, dir='.'):
    for filename in filenames:
        path = os.path.join(dir, filename)
        if os.path.exists(path):
            return path
    raise IOError('none found in %r: %r' % (dir, filenames))


def run_command(cmd, **kwargs):
    """Run command cmd and return the output."""
    logging.info('Executing %s %s' % (' '.join(cmd), kwargs))
    return subprocess.call(cmd, **kwargs)


def add_unexplained_error(dictionary, error):
    """
    Add *error* to the list of unexplained errors at
    dictionary['unexplained_errors']. Create the list if it does not
    exist yet.
    """
    key = 'unexplained_errors'
    dictionary.setdefault(key, [])
    if error not in dictionary[key]:
        dictionary[key].append(error)


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

    def add_unexplained_error(self, error):
        add_unexplained_error(self, error)

    def write(self):
        """Write the properties to disk."""
        assert self.filename
        makedirs(os.path.dirname(self.filename))
        write_file(self.filename, str(self))


class RunFilter(object):
    def __init__(self, filter, **kwargs):
        self.filters = make_list(filter or [])
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

    @staticmethod
    def apply_filter_to_run(filter_, run):
        # No need to copy the run as the original run is only needed if
        # the filter returns True. In this case modified_run is not changed.
        modified_run = run
        result = filter_(modified_run)
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
        for filter_ in self.filters:
            for old_run_id, run in list(props.items()):
                del props[old_run_id]
                modified_run = self.apply_filter_to_run(filter_, run)
                if modified_run:
                    # Filters may change a run's ID. Don't complain if ID is missing.
                    new_run_id = '-'.join(run['id']) if 'id' in run else old_run_id
                    props[new_run_id] = modified_run


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
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Exception as err:
            errors.append(err.args[0])
    if errors:
        raise Exception(errors)


def copy(src, dest, ignores=None):
    """
    Copies a file or directory to another file or directory.
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
    else:
        logging.critical('Path {} cannot be copied to {}'.format(
            os.path.abspath(src), os.path.abspath(dest)))


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


def product(values):
    """Compute the product of a sequence of numbers.

    >>> product([2, 3, 7])
    42
    """
    assert None not in values
    prod = 1
    for value in values:
        prod *= value
    return prod


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


def get_unexplained_errors_message(run):
    """
    Return an error message if an unexplained error occured in the given run,
    otherwise return None.
    """
    unexplained_errors = run.get('unexplained_errors', [])
    if not unexplained_errors or unexplained_errors == ['output-to-slurm.err']:
        return ''
    else:
        return (
            'Unexplained error(s): {unexplained_errors}. Please inspect'
            ' output and error logs under "{run_dir}".'.format(**run))


def get_slurm_err_content(src_dir):
    grid_steps_dir = src_dir.rstrip('/') + '-grid-steps'
    if os.path.exists(grid_steps_dir):
        slurm_err_filename = os.path.join(grid_steps_dir, 'slurm.err')
        if os.path.exists(slurm_err_filename):
            try:
                with open(slurm_err_filename) as f:
                    return f.read()
            except IOError:
                logging.error('Failed to read slurm.err file.')
        else:
            logging.error('File slurm.err is missing.')
    return ''


def filter_slurm_err_content(content):
    filtered = re.sub(
        r"slurmstepd: error: task/cgroup: unable to add task\[pid=\d+\]"
        r" to memory cg '\(null\)'\n", '', content)
    filtered = re.sub(r"\x00", '', filtered)
    return "\n".join(line for line in filtered.splitlines() if line.strip())


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


def get_argument_parser():
    def log_level(s):
        return getattr(logging, s.upper())

    parser = argparse.ArgumentParser(formatter_class=RawAndDefaultsHelpFormatter)
    parser.add_argument(
        '-l', '--log-level',
        type=log_level,
        dest='log_level',
        choices=['DEBUG', 'INFO', 'WARNING'],
        default='INFO',
        help='Logging verbosity')
    return parser

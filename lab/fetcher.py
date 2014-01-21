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

from glob import glob
import logging
import os
import subprocess

from lab import tools


class Fetcher(object):
    """
    Collect data from the runs of an experiment and store it in an evaluation
    directory.

    Use this class to combine data from multiple experiment or evaluation
    directories into a (new) evaluation directory.

    .. note::

        Using :py:meth:`exp.add_fetcher() <lab.experiment.Experiment.add_fetcher>`
        is more convenient.

    """
    def fetch_dir(self, run_dir, eval_dir, copy_all=False, run_filter=None, parsers=None):
        run_filter = run_filter or tools.RunFilter()
        parsers = parsers or []
        # Allow specyfing a list of multiple parsers or a single parser.
        if not isinstance(parsers, (tuple, list)):
            parsers = [parsers]
        # Make sure parsers is a list.
        parsers = list(parsers)

        prop_file = os.path.join(run_dir, 'properties')

        # Somehow '../..' gets inserted into sys.path and more strangely the
        # system lab.tools module gets called.
        # TODO: This HACK should be removed once the source of the error is clear.
        props = tools.Properties(filename=prop_file)
        if props.get('search_returncode') is not None and props.get("coverage") is None:
            logging.warning('search_parser.py exited abnormally for %s' % run_dir)
            logging.info('Rerunning search_parser.py')
            parsers.append(os.path.join(run_dir, '../../search_parser.py'))

        for parser in parsers:
            rel_parser = os.path.relpath(parser, start=run_dir)
            subprocess.call([rel_parser], cwd=run_dir)

        props = tools.Properties(filename=prop_file)
        props = run_filter.apply_to_run(props)
        if not props:
            return None, None
        run_id = props.get('id')
        # Abort if an id cannot be read.
        if not run_id:
            logging.critical('id is not set in %s.' % prop_file)

        if copy_all:
            dest_dir = os.path.join(eval_dir, *run_id)
            tools.makedirs(dest_dir)
            tools.fast_updatetree(run_dir, dest_dir, symlinks=True)

        return run_id, props

    def __call__(self, src_dir, eval_dir=None, copy_all=False, write_combined_props=True,
                 filter=None, parsers=None, **kwargs):
        """
        This method can be used to copy properties from an exp-dir or eval-dir
        into an eval-dir. If the destination eval-dir already exist, the data
        will be merged. This means *src_dir* can either be an exp-dir or an
        eval-dir and *eval_dir* can be a new or existing directory.

        If *copy_all* is True (default: False), copy all files from the run
        dirs to a new directory tree at *eval_dir*. Without this option only
        the combined properties file is written do disk.

        If *write_combined_props* is True (default), write the combined
        properties file.

        You can include only specific domains or configurations by using
        :py:class:`filters <.Report>`.

        *parsers* can be a list of paths to parser scripts. If given, each
        parser is called in each run directory and the results are added to
        the properties file which is fetched afterwards. This option is
        useful if you haven't parsed all or some values already during the
        experiment.

        Examples:

        Fetch all results and write a single combined properties file to the
        default evaluation directory (this step is added by default)::

            exp.add_step(Step('fetch', Fetcher(), exp.path))

        Read the combined properties file at ``<eval_dir1>/properties`` and
        merge it into the combined properties file at
        ``<combined_eval_dir>/properties``::

            exp.add_step(Step('combine', Fetcher(), eval_dir1, combined_eval_dir))

        Fetch only the runs for certain configuration from an older experiment::

            exp.add_step(Step('fetch', Fetcher(), src_dir,
                              filter_config_nick=['config_1', 'config_5']))
        """
        if not os.path.isdir(src_dir):
            logging.critical('%s is not a valid directory' % src_dir)
        run_filter = tools.RunFilter(filter, **kwargs)

        src_props = tools.Properties(filename=os.path.join(src_dir, 'properties'))
        fetch_from_eval_dir = 'runs' not in src_props or src_dir.endswith('-eval')
        if fetch_from_eval_dir:
            src_props = run_filter.apply(src_props)
            for prop in src_props.values():
                if prop.get('error', '').startswith('unexplained'):
                    logging.warning("Unexplained error in '%s': %s" %
                        (prop.get('run_dir'), prop.get('error')))

        eval_dir = eval_dir or src_dir.rstrip('/') + '-eval'
        logging.info('Fetching files from %s -> %s' % (src_dir, eval_dir))
        logging.info('Fetching from evaluation dir: %s' % fetch_from_eval_dir)

        if write_combined_props:
            # Load properties in the eval_dir if there are any already.
            combined_props = tools.Properties(os.path.join(eval_dir, 'properties'))
            if fetch_from_eval_dir:
                combined_props.update(src_props)

        # Get all run_dirs. None will be found if we fetch from an eval dir.
        run_dirs = sorted(glob(os.path.join(src_dir, 'runs-*-*', '*')))
        total_dirs = len(run_dirs)
        logging.info('Scanning properties from %d run directories' % total_dirs)
        unxeplained_errors = 0
        for index, run_dir in enumerate(run_dirs, start=1):
            loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
            logging.log(loglevel, 'Scanning: %6d/%d' % (index, total_dirs))
            run_id, props = self.fetch_dir(run_dir, eval_dir, copy_all=copy_all,
                                           run_filter=run_filter, parsers=parsers)
            if props is None:
                continue

            assert run_id, 'Dir %s has no id' % props.get('run_dir')
            if write_combined_props:
                combined_props['-'.join(run_id)] = props
            if props.get('error', '').startswith('unexplained'):
                logging.warning('Unexplained error in {run_dir}: {error}'.format(**props))
                unxeplained_errors += 1

        if unxeplained_errors:
            logging.warning('There were %d runs with unexplained errors.'
                            % unxeplained_errors)
        tools.makedirs(eval_dir)
        if write_combined_props:
            combined_props.write()

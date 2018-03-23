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
import sys

from lab import tools


def _check_eval_dir(eval_dir):
    if os.path.exists(eval_dir):
        answer = raw_input(
            '{} already exists. Do you want to (o)verwrite it, '
            '(m)erge the results, or (c)ancel? '.format(eval_dir)).strip().lower()
        if answer == 'o':
            tools.remove_path(eval_dir)
        elif answer == 'm':
            pass
        elif answer == 'c':
            sys.exit()
        else:
            # Abort for "cancel" and invalid answers.
            logging.critical('Invalid answer: "{}"'.format(answer))


class Fetcher(object):
    """
    Collect data from the runs of an experiment and store it in an
    evaluation directory.

    Use this class to combine data from multiple experiment or
    evaluation directories into a (new) evaluation directory.

    .. note::

        Using :py:meth:`exp.add_fetcher() <lab.experiment.Experiment.add_fetcher>`
        is more convenient.

    """
    def fetch_dir(self, run_dir):
        prop_file = os.path.join(run_dir, 'properties')
        return tools.Properties(filename=prop_file)

    def __call__(self, src_dir, eval_dir=None, merge=None, filter=None,
                 **kwargs):
        """
        This method can be used to copy properties from an exp-dir or
        eval-dir into an eval-dir. If the destination eval-dir already
        exist, the data will be merged. This means *src_dir* can either
        be an exp-dir or an eval-dir and *eval_dir* can be a new or
        existing directory.

        We recommend using lab.Experiment.add_fetcher() to add fetchers
        to an experiment. See the method's documentation for a
        description of the parameters.

        """
        if not os.path.isdir(src_dir):
            logging.critical('{} is missing or not a directory'.format(src_dir))
        run_filter = tools.RunFilter(filter, **kwargs)

        src_props = tools.Properties(
            filename=os.path.join(src_dir, 'static_experiment.properties'))
        fetch_from_eval_dir = 'runs' not in src_props or src_dir.endswith('-eval')

        eval_dir = eval_dir or src_dir.rstrip('/') + '-eval'
        logging.info('Fetching properties from {} to {}'.format(src_dir, eval_dir))

        if merge is None:
            _check_eval_dir(eval_dir)
        elif merge:
            # No action needed, data will be merged.
            pass
        else:
            tools.remove_path(eval_dir)

        # Load properties in the eval_dir if there are any already.
        combined_props = tools.Properties(os.path.join(eval_dir, 'properties'))
        if fetch_from_eval_dir:
            run_filter.apply(src_props)
            combined_props.update(src_props)
            logging.info('Fetched properties of {} runs.'.format(len(src_props)))
        else:
            try:
                slurm_err_content = tools.get_slurm_err_content(src_dir)
            except IOError:
                slurm_err_content = ''

            if slurm_err_content:
                filtered = tools.filter_slurm_err_content(slurm_err_content)
                logging.error(
                    'Slurm error log without "memory cg" errors:\n'
                    '{sep}\n{filtered}\n{sep}'.format(
                        sep='*' * 72, **locals()))

            new_props = tools.Properties()
            run_dirs = sorted(glob(os.path.join(src_dir, 'runs-*-*', '*')))
            total_dirs = len(run_dirs)
            logging.info(
                'Scanning properties from {:d} run directories'.format(total_dirs))
            for index, run_dir in enumerate(run_dirs, start=1):
                loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
                logging.log(loglevel, 'Scanning: {:6d}/{:d}'.format(index, total_dirs))
                props = self.fetch_dir(run_dir)
                if slurm_err_content:
                    props.add_unexplained_error('output-to-slurm.err')
                id_string = '-'.join(props['id'])
                new_props[id_string] = props
            run_filter.apply(new_props)
            combined_props.update(new_props)

        unexplained_errors = 0
        for props in combined_props.values():
            error_message = tools.get_unexplained_errors_message(props)
            if error_message:
                logging.error(error_message)
                unexplained_errors += 1

        tools.makedirs(eval_dir)
        combined_props.write()
        logging.info('Wrote properties file')

        if unexplained_errors:
            logging.critical(
                'There were {} runs with unexplained errors.'.format(
                    unexplained_errors))

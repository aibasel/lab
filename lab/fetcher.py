from glob import glob
import logging
import os

from lab import tools


class Fetcher(object):
    def fetch_dir(self, run_dir, eval_dir, copy_all=False):
        prop_file = os.path.join(run_dir, 'properties')
        props = tools.Properties(filename=prop_file)
        run_id = props.get('id')
        # Abort if an id cannot be read.
        if not run_id:
            logging.critical('id is not set in %s.' % prop_file)

        dest_dir = os.path.join(eval_dir, *run_id)
        if copy_all:
            tools.makedirs(dest_dir)
            tools.fast_updatetree(run_dir, dest_dir)

        return run_id, props

    def __call__(self, src_dir, eval_dir=None, copy_all=False, write_combined_props=True):
        """
        This method can be used to copy properties from exp-dirs or eval-dirs
        into eval-dirs. If the destination eval-dirs already exist, the data
        will be merged. This means src_dir can either be an exp-dir or an
        eval-dir and eval_dir can be a new or existing directory.

        copy_all: Copy all files from run dirs to a new directory tree.
                  Without this option only the combined properties file is
                  written do disk.

        write_combined_props: Write the combined properties file.
        """
        src_props = tools.Properties(filename=os.path.join(src_dir, 'properties'))
        fetch_from_eval_dir = 'runs' not in src_props or src_dir.endswith('-eval')

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
        for index, run_dir in enumerate(run_dirs, start=1):
            loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
            logging.log(loglevel, 'Fetching: %6d/%d' % (index, total_dirs))
            run_id, props = self.fetch_dir(run_dir, eval_dir, copy_all=copy_all)

            if write_combined_props:
                combined_props['-'.join(run_id)] = props

        logging.info('Fetching finished')
        tools.makedirs(eval_dir)
        if write_combined_props:
            combined_props.write()

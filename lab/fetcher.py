import cPickle
from glob import glob
import hashlib
import logging
import os
import sys

import tools


class Fetcher(object):
    def fetch_dir(self, run_dir, eval_dir, copy_all=False):
        prop_file = os.path.join(run_dir, 'properties')
        props = tools.Properties(prop_file)
        id = props.get('id')
        # Abort if an id cannot be read.
        if not id:
            logging.error('id is not set in %s.' % prop_file)
            sys.exit(1)

        dest_dir = os.path.join(eval_dir, *id)
        if copy_all:
            tools.makedirs(dest_dir)
            tools.fast_updatetree(run_dir, dest_dir)

        return '-'.join(id), props

    def __call__(self, exp_dir, eval_dir=None, copy_all=False, write_combined_props=True):
        """
        copy_all: Copy all files from run dirs to a new directory tree.
                  Without this option only the combined properties file is
                  written do disk.

        write_combined_props: Write the combined properties file.
        """
        exp_props = tools.Properties(os.path.join(exp_dir, 'properties'))
        total_dirs = exp_props.get('runs')

        assert not exp_dir.endswith('/')
        eval_dir = eval_dir or exp_dir + '-eval'
        logging.info('Fetching files from %s -> %s' % (exp_dir, eval_dir))

        if write_combined_props:
            combined_props_filename = os.path.join(eval_dir, 'properties')
            combined_props = tools.Properties(combined_props_filename)

        # Get all run_dirs
        run_dirs = sorted(glob(os.path.join(exp_dir, 'runs-*-*', '*')))
        for index, run_dir in enumerate(run_dirs, 1):
            logging.info('Fetching: %6d/%d' % (index, total_dirs))
            id_string, props = self.fetch_dir(run_dir, eval_dir, copy_all=copy_all)

            if write_combined_props:
                props['id-string'] = id_string
                combined_props[id_string] = props.dict()

        tools.makedirs(eval_dir)
        if write_combined_props:
            combined_props.write()
            self.write_data_dump(combined_props)

    def write_data_dump(self, combined_props):
        combined_props_file = combined_props.filename
        dump_path = combined_props_file.replace('properties', 'data_dump')
        logging.info('Reading properties file without parsing')
        properties_contents = open(combined_props_file).read()
        logging.info('Calculating properties hash')
        new_checksum = hashlib.md5(properties_contents).digest()
        data = combined_props.get_dataset()
        logging.info('Finished turning properties into dataset')
        # Pickle data for faster future use
        cPickle.dump((new_checksum, data), open(dump_path, 'wb'),
                     cPickle.HIGHEST_PROTOCOL)
        logging.info('Wrote data dump')

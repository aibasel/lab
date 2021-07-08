from glob import glob
import logging
import os
import sys

from lab import tools
import lab.experiment


def _check_eval_dir(eval_dir):
    if os.path.exists(eval_dir):
        answer = (
            input(
                f"{eval_dir} already exists. Do you want to (o)verwrite it, "
                f"(m)erge the results, or (c)ancel? "
            )
            .strip()
            .lower()
        )
        if answer == "o":
            tools.remove_path(eval_dir)
        elif answer == "m":
            pass
        elif answer == "c":
            sys.exit()
        else:
            # Abort for "cancel" and invalid answers.
            logging.critical(f'Invalid answer: "{answer}"')


class Fetcher:
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
        static_props = tools.Properties(
            filename=os.path.join(
                run_dir, lab.experiment.STATIC_RUN_PROPERTIES_FILENAME
            )
        )
        dynamic_props = tools.Properties(filename=os.path.join(run_dir, "properties"))

        props = tools.Properties()
        props.update(static_props)
        props.update(dynamic_props)

        driver_log = os.path.join(run_dir, "driver.log")
        if not os.path.exists(driver_log):
            props.add_unexplained_error(
                "driver.log is missing. Probably the run was never started."
            )

        driver_err = os.path.join(run_dir, "driver.err")
        run_err = os.path.join(run_dir, "run.err")
        for logfile in [driver_err, run_err]:
            if os.path.exists(logfile):
                with open(logfile) as f:
                    content = f.read()
                if content:
                    props.add_unexplained_error(
                        f"{os.path.basename(logfile)}: {content}"
                    )
        return props

    def __call__(self, src_dir, eval_dir=None, merge=None, filter=None, **kwargs):
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
            logging.critical(f"{src_dir} is missing or not a directory")
        run_filter = tools.RunFilter(filter, **kwargs)

        eval_dir = eval_dir or src_dir.rstrip("/") + "-eval"
        logging.info(f"Fetching properties from {src_dir} to {eval_dir}")

        if merge is None:
            _check_eval_dir(eval_dir)
        elif merge:
            # No action needed, data will be merged.
            pass
        else:
            tools.remove_path(eval_dir)

        # Load properties in the eval_dir if there are any already.
        combined_props = tools.Properties(os.path.join(eval_dir, "properties"))
        fetch_from_eval_dir = not os.path.exists(
            os.path.join(src_dir, "runs-00001-00100")
        )
        if fetch_from_eval_dir:
            src_props = tools.Properties(filename=os.path.join(src_dir, "properties"))
            run_filter.apply(src_props)
            combined_props.update(src_props)
            logging.info(f"Fetched properties of {len(src_props)} runs.")
        else:
            try:
                slurm_err_content = tools.get_slurm_err_content(src_dir)
            except FileNotFoundError:
                slurm_err_content = ""

            if slurm_err_content:
                logging.error("There was output to *-grid-steps/slurm.err")

            new_props = tools.Properties()
            run_dirs = sorted(glob(os.path.join(src_dir, "runs-*-*", "*")))
            total_dirs = len(run_dirs)
            logging.info(f"Scanning properties from {total_dirs:d} run directories")
            for index, run_dir in enumerate(run_dirs, start=1):
                loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
                logging.log(loglevel, f"Scanning: {index:6d}/{total_dirs:d}")
                props = self.fetch_dir(run_dir)
                if slurm_err_content:
                    props.add_unexplained_error("output-to-slurm.err")
                id_string = "-".join(props["id"])
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
        logging.info(
            f"Wrote properties file (contains {unexplained_errors} "
            f"runs with unexplained errors)."
        )

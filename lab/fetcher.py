import logging
from pathlib import Path
import sys

from lab import tools
import lab.experiment


def _check_eval_dir(eval_dir: Path):
    if eval_dir.exists():
        answer = (
            input(
                f"{tools.get_relative_path(eval_dir)} already exists. "
                f"Do you want to (o)verwrite it, "
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
        """Combine "static-properties" and "properties" from a run dir and return it."""
        run_dir = Path(run_dir)
        static_props = tools.Properties(
            filename=run_dir / lab.experiment.STATIC_RUN_PROPERTIES_FILENAME
        )
        dynamic_props_path = run_dir / "properties"
        dynamic_props = tools.Properties(filename=dynamic_props_path)
        if not dynamic_props_path.exists():
            logging.critical(
                f'Properties file "{tools.get_relative_path(dynamic_props_path)}" is'
                f' missing. Did you forget to add or run the "parse" step?'
            )
        elif not dynamic_props:
            logging.critical(
                f'Properties file "{tools.get_relative_path(dynamic_props_path)}" is'
                f" empty. Have you added at least one parser?"
            )

        props = tools.Properties()
        props.update(static_props)
        props.update(dynamic_props)

        driver_log = run_dir / "driver.log"
        if not driver_log.exists():
            props.add_unexplained_error(
                "driver.log is missing. Probably the run was never started."
            )

        driver_err = run_dir / "driver.err"
        run_err = run_dir / "run.err"
        for logfile in [driver_err, run_err]:
            if logfile.exists():
                content = logfile.read_text()
                if content:
                    props.add_unexplained_error(f"{logfile.name}: {content}")
        return props

    def __call__(self, src_dir, eval_dir=None, merge=None, filter=None, **kwargs):
        """
        Copy properties from an exp-dir or eval-dir into an eval-dir.

        If the destination eval-dir already exist, the data will be merged. This
        means *src_dir* can be an exp-dir, an eval-dir or a properties file, and
        *eval_dir* can be a new or existing destination directory.

        We recommend using lab.Experiment.add_fetcher() to add fetchers to an
        experiment. See the method's documentation for a description of the
        parameters.

        """
        src_dir = Path(src_dir)
        if not src_dir.exists():
            logging.critical(f"{src_dir} is missing")

        if src_dir.is_file():
            src_props_file = src_dir
        else:
            src_props_file = src_dir / "properties"
        run_filter = tools.RunFilter(filter, **kwargs)

        eval_dir = eval_dir or str(src_dir).rstrip("/") + "-eval"
        eval_dir = Path(eval_dir)
        logging.info(
            f"Fetching properties from {tools.get_relative_path(src_dir)} "
            f"to {tools.get_relative_path(eval_dir)}"
        )

        if merge is None:
            _check_eval_dir(eval_dir)
        elif merge:
            # No action needed, data will be merged.
            pass
        else:
            tools.remove_path(eval_dir)

        # Load properties in the eval_dir if there are any already.
        fetch_from_eval_dir = src_props_file.exists()
        combined_props = tools.Properties(eval_dir / "properties")
        if fetch_from_eval_dir:
            src_props = tools.Properties(filename=src_props_file)
            if not src_props:
                logging.critical(f"No properties found in {src_dir}")
            run_filter.apply(src_props)
            combined_props.update(src_props)
            logging.info(f"Fetched properties of {len(src_props)} runs.")
        else:
            try:
                slurm_err_content = tools.get_slurm_err_content(src_dir)
            except FileNotFoundError:
                slurm_err_content = ""

            if slurm_err_content:
                logging.warning("There was output to *-grid-steps/slurm.err")

            new_props = tools.Properties()
            run_dirs = sorted(src_dir.glob("runs-*-*/*"))
            num_dirs = len(run_dirs)
            logging.info(f"Collecting properties from {num_dirs:d} run directories")
            for index, run_dir in enumerate(run_dirs, start=1):
                props = self.fetch_dir(run_dir)
                if slurm_err_content:
                    props.add_unexplained_error("output-to-slurm.err")
                id_string = "-".join(props["id"])
                new_props[id_string] = props
                loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
                logging.log(
                    loglevel, f"Collected {index:6d}/{num_dirs} properties files"
                )
            run_filter.apply(new_props)
            combined_props.update(new_props)

        unexplained_errors = 0
        for props in combined_props.values():
            if tools.has_unexplained_error(props):
                unexplained_errors += 1

        tools.makedirs(eval_dir)
        combined_props.write()
        func = logging.info if unexplained_errors == 0 else logging.warning
        func(
            f"Wrote properties file. It contains {unexplained_errors} "
            f"runs with unexplained errors."
        )

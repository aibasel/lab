import json
import logging
import sys
from pathlib import Path

import lab.experiment
from lab import tools
from lab.archive import ExperimentArchive


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
        dynamic_props_path = run_dir / "properties"
        return _combine_run_properties(
            static_props=tools.Properties(
                filename=run_dir / lab.experiment.STATIC_RUN_PROPERTIES_FILENAME
            ),
            dynamic_props=tools.Properties(filename=dynamic_props_path),
            dynamic_props_name=tools.get_relative_path(dynamic_props_path),
            has_dynamic_props=dynamic_props_path.exists(),
            has_driver_log=(run_dir / "driver.log").exists(),
            logs={
                name: (run_dir / name).read_text()
                for name in ["driver.err", "run.err"]
                if (run_dir / name).exists()
            },
        )

    def _fetch_archive(self, archive_path):
        """Yield the combined properties of each run in an experiment archive."""
        archive = ExperimentArchive(archive_path)
        with archive.reader() as tar:
            members = {member.name: member for member in tar}
            groups = archive.group_by_run_dir(members)
            run_dirs = sorted(run_dir for run_dir in groups if run_dir is not None)
            num_runs = len(run_dirs)
            logging.info(f"Collecting properties from {num_runs:d} archived runs")

            def read(name):
                return tar.extractfile(members[name]).read().decode()

            def read_props(name):
                props = tools.Properties()
                if name in members:
                    props.update(json.loads(read(name)))
                return props

            for index, run_dir in enumerate(run_dirs, start=1):
                props_name = f"{run_dir}/properties"
                _log_progress(index, num_runs)
                yield _combine_run_properties(
                    static_props=read_props(
                        f"{run_dir}/{lab.experiment.STATIC_RUN_PROPERTIES_FILENAME}"
                    ),
                    dynamic_props=read_props(props_name),
                    dynamic_props_name=f"{archive_path}:{props_name}",
                    has_dynamic_props=props_name in members,
                    has_driver_log=f"{run_dir}/driver.log" in members,
                    logs={
                        name: read(f"{run_dir}/{name}")
                        for name in ["driver.err", "run.err"]
                        if f"{run_dir}/{name}" in members
                    },
                )

    def _fetch_dirs(self, src_dir):
        """Yield the combined properties of each run in an experiment directory."""
        run_dirs = sorted(src_dir.glob("runs-*-*/*"))
        num_dirs = len(run_dirs)
        logging.info(f"Collecting properties from {num_dirs:d} run directories")
        for index, run_dir in enumerate(run_dirs, start=1):
            _log_progress(index, num_dirs)
            yield self.fetch_dir(run_dir)

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
        # Configure logging here so that logging.critical() aborts the program
        # even when a fetcher is run without constructing an Experiment.
        tools.configure_logging()
        src_dir = Path(src_dir)
        if not src_dir.exists():
            logging.critical(f"{src_dir} is missing")
        is_archive = src_dir.suffix == ".tar"
        # For archived experiments, the eval and grid-steps directories are
        # named after the experiment directory.
        exp_dir = src_dir.with_suffix("") if is_archive else src_dir

        eval_dir = eval_dir or str(exp_dir).rstrip("/") + "-eval"
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
        src_props_file = src_dir / "properties"
        for path in [src_dir / "properties.xz", src_dir]:
            if not src_props_file.is_file() and path.is_file():
                src_props_file = path
                break
        fetch_from_eval_dir = not is_archive and src_props_file.exists()
        combined_props = tools.Properties(eval_dir / "properties")
        run_filter = tools.RunFilter(filter, **kwargs)
        if fetch_from_eval_dir:
            src_props = tools.Properties(filename=src_props_file)
            if not src_props:
                logging.critical(f"No properties found in {src_dir}")
            run_filter.apply(src_props)
            combined_props.update(src_props)
            logging.info(f"Fetched properties of {len(src_props)} runs.")
        else:
            try:
                slurm_err_content = tools.get_slurm_err_content(exp_dir)
            except FileNotFoundError:
                slurm_err_content = ""

            if slurm_err_content:
                logging.warning("There was output to *-grid-steps/slurm.err")

            new_props = tools.Properties()
            runs = (
                self._fetch_archive(src_dir)
                if is_archive
                else self._fetch_dirs(src_dir)
            )
            for props in runs:
                if slurm_err_content:
                    props.add_unexplained_error("output-to-slurm.err")
                id_string = "-".join(props["id"])
                new_props[id_string] = props
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


def _combine_run_properties(
    static_props,
    dynamic_props,
    dynamic_props_name,
    has_dynamic_props,
    has_driver_log,
    logs,
):
    if not has_dynamic_props:
        logging.critical(
            f'Properties file "{dynamic_props_name}" is'
            f' missing. Did you forget to add or run the "parse" step?'
        )
    elif not dynamic_props:
        logging.critical(
            f'Properties file "{dynamic_props_name}" is'
            f" empty. Have you added at least one parser?"
        )

    props = tools.Properties()
    props.update(static_props)
    props.update(dynamic_props)

    if not has_driver_log:
        props.add_unexplained_error(
            "driver.log is missing. Probably the run was never started."
        )

    for name, content in logs.items():
        if content:
            props.add_unexplained_error(f"{name}: {content}")
    return props


def _log_progress(index, num_runs):
    loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
    logging.log(loglevel, f"Collected {index:6d}/{num_runs} properties files")

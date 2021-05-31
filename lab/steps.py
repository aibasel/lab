import logging
import shutil
import traceback


class Step:
    """
    When the step is executed *args* and *kwargs* will be passed to the
    callable *func*. ::

        exp.add_step('show-disk-usage', subprocess.call, ['df'])

    """

    def __init__(self, name, func, *args, **kwargs):
        assert func is not None
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._funcname = (
            getattr(func, "__name__", None) or func.__class__.__name__.lower()
        )

    def __call__(self):
        if self.func is None:
            logging.critical("You cannot run the same step more than once")
        logging.info(f"Running step {self.name}: {self}")
        try:
            retval = self.func(*self.args, **self.kwargs)
            # Free memory
            self.func = None
            if retval:
                logging.critical(f"An error occured in step {self.name}.")
            return retval
        except (ValueError, TypeError):
            traceback.print_exc()
            logging.critical(f"Could not run step {self}")

    def __str__(self):
        name = self._funcname
        args = ", ".join(repr(arg) for arg in self.args)
        sep = ", " if self.args and self.kwargs else ""
        kwargs = ", ".join(f"{k}={v!r}" for (k, v) in sorted(self.kwargs.items()))
        return f"{name}({args}{sep}{kwargs})"


def _get_step_index(steps, step_name):
    for index, step in enumerate(steps):
        if step.name == step_name:
            return index
    logging.critical(f'There is no step called "{step_name}"')


def get_step(steps, step_name):
    """*step_name* can be a step's name or number."""
    if step_name.isdigit():
        try:
            return steps[int(step_name) - 1]
        except IndexError:
            logging.critical(f"There is no step number {step_name}")
    return steps[_get_step_index(steps, step_name)]


def get_steps_text(steps):
    # Use width 0 if no steps have been added.
    name_width = min(max([len(step.name) for step in steps] + [0]), 50)
    terminal_width = shutil.get_terminal_size().columns
    lines = ["Available steps:", "================"]
    for number, step in enumerate(steps, start=1):
        line = " ".join([str(number).rjust(2), step.name.ljust(name_width)])
        step_text = str(step)
        if len(line) + len(step_text) < terminal_width:
            lines.append(line + " " + step_text)
        else:
            lines.extend(["", line, step_text, ""])
    return "\n".join(lines)

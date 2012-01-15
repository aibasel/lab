import getpass
import os
import logging
import shutil
from subprocess import call


class Step(object):
    def __init__(self, name, func, *args, **kwargs):
        """
        When the step is executed args and kwargs will be passed to the
        callable func.
        """
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        try:
            return self.func(*self.args, **self.kwargs)
        except (ValueError, TypeError):
            import traceback
            traceback.print_exc()
            logging.critical('Could not run step: %s' % self)

    def __str__(self):
        funcname = getattr(self.func, '__name__', None) or self.func.__class__.__name__
        return '%s(%s%s%s)' % (funcname,
                               ', '.join([repr(arg) for arg in self.args]),
                               ', ' if self.args and self.kwargs else '',
                               ', '.join(['%s=%s' % (k, repr(v)) for (k, v) in self.kwargs.items()]))

    @classmethod
    def publish_reports(cls, *report_files):
        user = getpass.getuser()

        def publish_reports():
            for path in report_files:
                name = os.path.basename(path)
                dest = os.path.join(os.path.expanduser('~'), '.public_html/', name)
                shutil.copy2(path, dest)
                print 'Copied report to file://%s' % dest
                print 'http://www.informatik.uni-freiburg.de/~%s/%s' % (user, name)

        return cls('publish_reports', publish_reports)

    @classmethod
    def zip_exp_dir(cls, exp):
        return cls('zip-exp-dir', call, ['tar', '-czf', exp.name + '.tar.gz', exp.name],
                   cwd=os.path.dirname(exp.path))

    @classmethod
    def remove_exp_dir(cls, exp):
        return cls('remove-exp-dir', shutil.rmtree, exp.path)


class Sequence(list):
    def process_step_names(self, names):
        for step_name in names:
            self.process_step_name(step_name)

    def process_step_name(self, step_name):
        if step_name.isdigit():
            try:
                step = self[int(step_name) - 1]
            except IndexError:
                logging.critical('There is no step number %s' % step_name)
            self.run_step(step)
        elif step_name == 'next':
            raise NotImplementedError
        elif step_name == 'all':
            # Run all steps
            for step in self:
                self.run_step(step)
        else:
            for step in self:
                if step.name == step_name:
                    self.run_step(step)
                    return
            logging.critical('There is no step called %s' % step_name)

    def run_step(self, step):
        logging.info('Running %s: %s' % (step.name, step))
        returnval = step()
        if returnval:
            logging.critical('An error occured in %s, the return value was %s' % (step, returnval))

    def get_steps_text(self):
        lines = ['Available steps:', '================']
        for number, step in enumerate(self, start=1):
            lines.append(' '.join([str(number).rjust(2), step.name.ljust(30), str(step)]))
        return '\n'.join(lines)

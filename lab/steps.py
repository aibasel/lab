import getpass
import logging
import shutil


class Step(object):
    def __init__(self, name, func, *args, **kwargs):
        """
        When the step is executed args and kwargs will be passed to the
        callable func.
        A step's returncode is saved in an instance variable.
        If bool(step.returncode) == True then we do not automatically proceed
        to the next step.
        """
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        try:
            return self.func(*self.args, **self.kwargs)
        except (ValueError, TypeError):
            logging.error('Could not run step: %s' % self)
            import traceback
            traceback.print_exc()
            return 1

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


class Sequence(list):
    #def __init__(self, *args, **kwargs):
    #    list.__init__(self, *args, **kwargs)

    def process_step_name(self, step_name):
        if step_name.isdigit():
            try:
                step = self[int(step_name) - 1]
            except IndexError:
                logging.error('There is no step number %s' % step_name)
                sys.exit(1)
            self.run_step(step)
        elif step_name == 'next':
            raise NotImplementedError
        elif step_name == 'all':
            # Run all steps
            for step in self.steps:
                error = self.run_step(step)
                if error:
                    break
        else:
            for step in self:
                if step.name == step_name:
                    self.run_step(step)
                    return
            logging.error('There is no step called %s' % step_name)

    def run_step(self, step):
        logging.info('Running %s: %s' % (step.name, step))
        returnval = step()
        if returnval:
            logging.error('An error occured in %s' % step)
            logging.error('The return value was: %s' % returnval)
            return True
        return False

    def get_steps_text(self):
        lines = ['Available steps:', '================']
        for number, step in enumerate(self, start=1):
            lines.append(' '.join([str(number).rjust(2), step.name.ljust(30), str(step)]))
        return '\n'.join(lines)

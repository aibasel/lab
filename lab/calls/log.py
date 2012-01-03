from lab.tools import Properties

redirects = {'stdout': open('run.log', 'a'), 'stderr': open('run.err', 'a')}
driver_log = open('driver.log', 'a')
driver_err = open('driver.err', 'a')


def print_(stream, text):
    stream.write('%s\n' % text)
    stream.flush()

def set_property(name, value):
    properties = Properties(filename='properties')
    properties[name] = value
    properties.write()

def save_returncode(command_name, value):
    set_property('%s_returncode' % command_name.lower(), str(value))
    error = 0 if value == 0 else 1
    set_property('%s_error' % command_name.lower(), error)

redirects = {'stdout': open('run.log', 'a'), 'stderr': open('run.err', 'a')}
driver_log = open('driver.log', 'a')
driver_err = open('driver.err', 'a')
properties_file = open('properties', 'a')


def print_(stream, text):
    stream.write('%s\n' % text)
    stream.flush()

def add_property(name, value):
    print_(properties_file, '%s = %s' % (name, repr(value)))

def save_returncode(command_name, value):
    add_property('%s_returncode' % command_name.lower(), str(value))
    error = 0 if value == 0 else 1
    add_property('%s_error' % command_name.lower(), error)

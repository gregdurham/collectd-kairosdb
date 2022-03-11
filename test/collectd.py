# class collectd:
#
import sys

"""
Emulates collectd modules for testing purposes
"""

config_method = None
init_method = None
write_method = None
write_data = None

def register_config(config):
    global config_method
    config_method = config


def register_init(init):
    global init_method
    init_method = init


def register_write(write, data):
    global write_method, write_data
    write_method = write
    write_data = data


def get_data():
    return write_data


def info(message):
    print('INFO: ', message, file=sys.stderr)


def error(message):
    print('ERROR: ', message, file=sys.stderr)


def debug(message):
    print('DEBUG: ', message, file=sys.stderr)


def warning(message):
    print('WARNING: ', message, file=sys.stderr)

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
    print >> sys.stderr, 'INFO: %s' % message


def error(message):
    print >> sys.stderr, 'ERROR: %s' % message


def debug(message):
    print >> sys.stderr, 'DEBUG: %s' % message


def warning(message):
    print >> sys.stderr, 'WARNING: %s' % message

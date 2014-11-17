# Copyright 2013 Gregory Durham
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import collectd
import socket
import httplib
from string import maketrans
from time import time
from traceback import format_exc

add_host_tag = True
host = None
port = None
types = {}
metric_name = 'collectd.%(plugin)s.%(plugin_instance)s.%(type)s.%(type_instance)s'
tags_string = ""
host_separator = "_"
metric_separator = "."
protocol = "telnet"


def kairosdb_parse_types_file(path):
    global types

    f = open(path, 'r')

    for line in f:
        fields = line.split()
        if len(fields) < 2:
            continue

        type_name = fields[0]

        if type_name[0] == '#':
            continue

        v = []
        for ds in fields[1:]:
            ds = ds.rstrip(',')
            ds_fields = ds.split(':')

            if len(ds_fields) != 4:
                collectd.warning('kairosdb_writer: cannot parse data source %s on type %s' % (ds, type_name))
                continue

            v.append(ds_fields)

        types[type_name] = v

    f.close()


def str_to_num(s):
    """
    Convert type limits from strings to floats for arithmetic.
    Will force U[nlimited] values to be 0.
    """

    try:
        n = float(s)
    except ValueError:
        n = 0

    return n


def sanitize_field(field):
    """
    Santize Metric Fields: replace dot and space with metric_separator. Delete
    parentheses and quotes. Convert to lower case if configured to do so.
    """
    field = field.strip()
    trans = maketrans(' .', metric_separator * 2)
    field = field.translate(trans, '()')
    field = field.replace('"', '')
    if lowercase_metric_names:
        field = field.lower()
    return field


def kairosdb_config(c):
    global host, port, host_separator, \
        metric_separator, lowercase_metric_names, protocol, \
        tags_string, metric_name, add_host_tag

    for child in c.children:
        if child.key == 'AddHostTag':
            add_host_tag = child.values[0]
        elif child.key == 'KairosDBHost':
            host = child.values[0]
        elif child.key == 'KairosDBPort':
            port = int(child.values[0])
        elif child.key == 'TypesDB':
            for v in child.values:
                kairosdb_parse_types_file(v)
        elif child.key == 'LowercaseMetricNames':
            lowercase_metric_names = child.values[0]
        elif child.key == 'MetricName':
            metric_name = str(child.values[0])
        elif child.key == 'HostSeparator':
            host_separator = child.values[0]
        elif child.key == 'MetricSeparator':
            metric_separator = child.values[0]
        elif child.key == 'KairosDBProtocol':
            protocol = str(child.values[0]).lower()
        elif child.key == 'Tags':
            for v in child.values:
                tags_string += "%s " % v

    tags_string = tags_string.replace('.', host_separator)

    if not host:
        raise Exception('KairosDBHost not defined')

    if not port:
        raise Exception('KairosDBPort not defined')

    if not tags_string:
        raise Exception('Tags not defined')

    if protocol != 'http' and protocol != 'telnet':
        raise Exception('Invalid protocol specified. Must be either "http" or "telnet"')

    collectd.info('Initializing kairosdb_writer client in %s mode.' % protocol.upper())


def kairosdb_init():
    import threading

    d = {
        'host': host,
        'port': port,
        'lowercase_metric_names': lowercase_metric_names,
        'conn': None,
        'lock': threading.Lock(),
        'values': {},
        'last_connect_time': 0
    }

    kairosdb_connect(d)

    collectd.register_write(kairosdb_write, data=d)


def kairosdb_connect(data):
    if not data['conn'] and protocol == 'http':
        data['conn'] = httplib.HTTPConnection(host, port)
        return True

    elif not data['conn'] and protocol == 'telnet':
        # only attempt reconnect every 10 seconds if protocol of type Telnet
        now = time()
        if now - data['last_connect_time'] < 10:
            return False

        data['last_connect_time'] = now
        collectd.info('connecting to %s:%s' % (data['host'], data['port']))
        try:
            data['conn'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data['conn'].connect((host, port))
            return True
        except:
            collectd.error('error connecting socket: %s' % format_exc())
            return False
    else:
        return True


def kairosdb_send_telnet_data(data, s):
    result = False
    data['lock'].acquire()

    try:
        if protocol == 'telnet':
            data['conn'].sendall(s)
            result = True
    except socket.error, e:
        data['conn'] = None
        if isinstance(e.args, tuple):
            collectd.warning('kairosdb_writer: socket error %d' % e[0])
        else:
            collectd.warning('kairosdb_writer: socket error')
    except:
        collectd.warning('kairosdb_writer: error sending data: %s' % format_exc())

    data['lock'].release()
    return result


def kairosdb_send_http_data(data, json):
    collectd.debug('Json=%s' % json)
    data['lock'].acquire()

    response = ''
    try:
        headers = {'Content-type': 'application/json', 'Connection': 'keep-alive'}
        data['conn'].request('POST', '/api/v1/datapoints', json, headers)
        res = data['conn'].getresponse()
        response = res.read()
        collectd.debug('Response code: %d' % res.status)

        if res.status == 204:
            exit_code = True
        else:
            collectd.error(response)
            exit_code = False

    except httplib.ImproperConnectionState, e:
        collectd.error('Lost connection to kairosdb server: %s' % e.message)
        data['conn'] = None
        exit_code = False

    except httplib.HTTPException, e:
        collectd.error('Error sending http data: %s' % e.message)
        if response:
            collectd.error(response)
        exit_code = False

    except Exception, e:
        collectd.error('Error sending http data: %s' % str(e))
        exit_code = False

    data['lock'].release()
    return exit_code


def kairosdb_write(v, data=None):
    data['lock'].acquire()
    if not kairosdb_connect(data) and (protocol == 'telnet' or protocol == 'http'):
        data['lock'].release()
        collectd.warning('kairosdb_writer: no connection to kairosdb server')
        return

    data['lock'].release()

    if v.type not in types:
        collectd.warning('kairosdb_writer: do not know how to handle type %s. do you have all your types.db files configured?' % v.type)
        return

    v_type = types[v.type]

    if len(v_type) != len(v.values):
        collectd.warning('kairosdb_writer: differing number of values for type %s' % v.type)
        return

    hostname = v.host.replace('.', host_separator)

    tags = tags_string
    if add_host_tag:
        tags += "host=%s" % hostname

    plugin = v.plugin
    plugin_instance = ''
    if v.plugin_instance:
        plugin_instance = sanitize_field(v.plugin_instance)

    type_name = v.type
    type_instance = ''
    if v.type_instance:
        type_instance = sanitize_field(v.type_instance)

    name = metric_name % {'host': hostname, 'plugin': plugin, 'plugin_instance': plugin_instance, 'type': type_name, 'type_instance': type_instance}

    # Remove dots for missing pieces
    name = name.replace('..', '.')
    name = name.rstrip('.')

    if protocol == 'http':
        kairosdb_write_http_metrics(data, v_type, v, name, tags)
    else:
        kairosdb_write_telnet_metrics(data, v_type, v, name, tags)


def kairosdb_write_telnet_metrics(data, types_list, v, name, tags):
    # we update shared recorded values, so lock to prevent race conditions
    data['lock'].acquire()

    timestamp = v.time

    lines = []
    i = 0
    for value in v.values:
        ds_name = types_list[i][0]
        name += ".%s" % ds_name
        new_value = value
        collectd.debug("metric name= %s" % name)

        if new_value is not None:
            line = 'put %s %d %f %s' % (name, timestamp, new_value, tags)
            collectd.debug(line)
            lines.append(line)

        i += 1

    data['lock'].release()

    lines.append('')
    kairosdb_send_telnet_data(data, '\n'.join(lines))


def kairosdb_write_http_metrics(data, types_list, v, name, tags):
    # we update shared recorded values, so lock to prevent race conditions
    data['lock'].acquire()

    timestamp = v.time * 1000
    json = '['
    i = 0
    for value in v.values:
        ds_name = types_list[i][0]
        name += ".%s" % ds_name
        new_value = value
        collectd.debug("metric name= %s" % name)

        if new_value is not None:
            if i > 0:
                json += ','

            json += '{'
            json += '"name":"%s",' % name
            json += '"datapoints":[[%d, %f]],' % (timestamp, new_value)
            json += '"tags": {'

            tag_list = tags.split(' ')
            first = True
            for tag in tag_list:
                if tag:
                    if first:
                        first = False
                    else:
                        json += ", "

                    tag_parts = tag.split("=")
                    if len(tag_parts) == 2:
                        json += '"%s": "%s"' % (tag_parts[0], tag_parts[1])
                    else:
                        collectd.error("Invalid tag: %s" % tag)
            json += '}'

            json += '}'
        i += 1

    data['lock'].release()

    json += ']'

    collectd.debug(json)
    kairosdb_send_http_data(data, json)


collectd.register_config(kairosdb_config)
collectd.register_init(kairosdb_init)

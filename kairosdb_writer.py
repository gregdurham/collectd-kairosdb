# Copyright 2013 Gregory Durham
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Version 1.2

# noinspection PyUnresolvedReferences
import collectd
import traceback
import socket
import httplib
import imp
import os
from string import maketrans
from time import time
import datetime
from traceback import format_exc
import threading


class KairosdbWriter:

    def __init__(self):
        self.add_host_tag = True
        self.convert_rates = []
        self.uri = None
        self.types = {}
        self.metric_name = 'collectd.%(plugin)s.%(plugin_instance)s.%(type)s.%(type_instance)s'
        self.tags_map = {}
        self.host_separator = "."
        self.metric_separator = "."
        self.formatter = None
        self.pluginsToFormatter = None
        self.counters_map = {}  # store the last value and timestamp for each value of type from DERIVE and COUNTER
        self.lowercase_metric_names = False
        self.protocol = None
        self.samples_sent = 0
        self.samples_dropped = 0
        self.samples_error = 0
        self.verbose_logging = False
        self.throwaway_sample_age = False

    def kairosdb_parse_types_file(self, path):
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

            self.types[type_name] = v

        f.close()

    @staticmethod
    def str_to_num(s):
        """
        Convert type limits from strings to floats for arithmetic.
        Will force unlimited values to be 0.
        """

        try:
            n = float(s)
        except ValueError:
            n = 0

        return n

    def sanitize_field(self, field):
        """
        Sanitize Metric Fields: replace dot and space with metric_separator. Delete
        parentheses and quotes. Convert to lower case if configured to do so.
        """
        field = field.strip()
        trans = maketrans(' .', self.metric_separator * 2)
        field = field.translate(trans, '()')
        field = field.replace('"', '')
        if self.lowercase_metric_names:
            field = field.lower()
        return field

    def kairosdb_config(self, c):
        for child in c.children:
            if child.key == 'AddHostTag':
                self.add_host_tag = child.values[0]
            elif child.key == 'KairosDBURI':
                self.uri = child.values[0]
            elif child.key == 'TypesDB':
                for tag in child.values:
                    self.kairosdb_parse_types_file(tag)
            elif child.key == 'LowercaseMetricNames':
                self.lowercase_metric_names = child.values[0]
            elif child.key == 'MetricName':
                self.metric_name = str(child.values[0])
            elif child.key == 'HostSeparator':
                self.host_separator = child.values[0]
            elif child.key == 'MetricSeparator':
                self.metric_separator = child.values[0]
            elif child.key == 'ConvertToRate':
                if not child.values:
                    raise Exception("Missing ConvertToRate values")
                self.convert_rates = child.values
            elif child.key == 'Formatter':
                formatter_path = child.values[0]
                try:
                    self.formatter = imp.load_source('formatter', formatter_path)
                except:
                    raise Exception('Could not load formatter %s %s' % (formatter_path, format_exc()))
            elif child.key == "PluginFormatterPath":
                if child.values:
                    self.pluginsToFormatter = self.load_plugin_formatters(child.values[0])
            elif child.key == 'Tags':
                for tag in child.values:
                    tag_parts = tag.split("=")
                    if len(tag_parts) == 2 and len(tag_parts[0]) > 0 and len(tag_parts[1]) > 0:
                        self.tags_map[tag_parts[0]] = tag_parts[1]
                    else:
                        raise Exception("Invalid tag: %s" % tag)
            elif child.key == 'ThrowawaySampleAge':
                if not child.values:
                    raise Exception("Missing %s value, must be in seconds" % child.key)
                try:
                   self.throwaway_sample_age = int(child.values[0])
                except Exception as ex:
                    self.throwaway_sample_age = False
                    raise Exception("%s requires time in seconds: %s" % (child.key, str(ex)))
            elif child.key == 'VerboseLogging':
                if isinstance(child.values[0], bool):
                    self.verbose_logging = bool(child.values[0])
                elif isinstance(child.values[0], str):
                    if str.lower(child.values[0]) == 'true':
                        self.verbose_logging = True
                    else:
                        self.verbose_logging = False

    def kairosdb_init(self):
        # Param validation has to happen here, exceptions thrown in kairosdb_config
        # do not prevent the plugin from loading.
        if not self.uri:
            raise Exception('KairosDBURI not defined')

        if not self.tags_map and not self.add_host_tag:
            raise Exception('Tags not defined')

        split = self.uri.strip('/').split(':')
        # collectd.info(repr(split))
        if len(split) != 3 and len(split) != 2:
            raise Exception('KairosDBURI must be in the format of <protocol>://<host>[:<port>]')

        # validate protocol and set default ports
        self.protocol = split[0]
        if self.protocol == 'http':
            port = 80
        elif self.protocol == 'https':
            port = 443
        elif self.protocol == 'telnet':
            port = 4242
        else:
            raise Exception('Invalid protocol specified. Must be either "http", "https" or "telnet"')

        host = split[1].strip('/')

        if len(split) == 3:
            port = int(split[2])

        collectd.info('Initializing kairosdb_writer client in %s mode.' % self.protocol.upper())

        d = {
            'host': host,
            'port': port,
            'lowercase_metric_names': self.lowercase_metric_names,
            'conn': None,
            'lock': threading.Lock(),
            'values': {},
            'last_connect_time': 0
        }

        self.kairosdb_connect(d)

        collectd.register_write(self.kairosdb_write, data=d)

    def kairosdb_connect(self, data):
        # collectd.info(repr(data))
        if not data['conn'] and self.protocol == 'http':
            try:
                collectd.info("connecting pid=%d host=%s port=%s proto=%s" % (os.getpid(), data['host'], data['port'], self.protocol))
                data['conn'] = httplib.HTTPConnection(data['host'], data['port'])
                return True
            except:
                collectd.error('error connecting to http connection: %s' % format_exc())
                return False

        elif not data['conn'] and self.protocol == 'https':
            try:
                collectd.info("connecting pid=%d host=%s port=%s proto=%s" % (os.getpid(), data['host'], data['port'], self.protocol))
                data['conn'] = httplib.HTTPSConnection(data['host'], data['port'])
                return True
            except:
                collectd.error('error connecting to https connection: %s' % format_exc())
                return False

        elif not data['conn'] and self.protocol == 'telnet':
            # only attempt reconnect every 10 seconds if protocol of type Telnet
            now = time()
            if now - data['last_connect_time'] < 10:
                return False

            data['last_connect_time'] = now
            collectd.info('connecting to %s:%s' % (data['host'], data['port']))

            # noinspection PyBroadException
            try:
                data['conn'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data['conn'].connect((data['host'], data['port']))
                return True
            except:
                collectd.error('error connecting socket: %s' % format_exc())
                return False
        else:
            return True

    @staticmethod
    def reset_connection(data):
        collectd.error('Resetting connection to kairosdb server')
        data['conn'].close()
        data['conn'] = None

    def kairosdb_send_telnet_data(self, data, s):
        result = False
        with data['lock']:
            if not self.kairosdb_connect(data):
                collectd.warning('kairosdb_writer: no connection to kairosdb server')
                return

            # noinspection PyBroadException
            try:
                if self.protocol == 'telnet':
                    data['conn'].sendall(s)
                    result = True
            except socket.error, e:
                self.reset_connection(data)
                if isinstance(e.args, tuple):
                    collectd.warning('kairosdb_writer: socket error %d' % e[0])
                else:
                    collectd.warning('kairosdb_writer: socket error')
            except:
                self.reset_connection(data)
                collectd.warning('kairosdb_writer: error sending data: %s' % format_exc())

            return result

    def kairosdb_send_http_data(self, data, json, ts, name):
        collectd.debug('Json=%s' % json)
        with data['lock']:
            if len(json) < 1 or json == '[]':
                # No data
                return
            if not self.kairosdb_connect(data):
                collectd.warning('kairosdb_writer: no connection to kairosdb server')
                return

            ts_diff = time() - ts
            ts_diff_m = ts_diff / 60
            to_send = True
    
            if self.throwaway_sample_age and ts_diff > self.throwaway_sample_age:
                to_send = False
    
            if to_send:
                sent_decision = 'sent'
                with data['lock']:
                    if not self.kairosdb_connect(data):
                        collectd.warning('kairosdb_writer: no connection to kairosdb server')
                        return
    
                    response = ''
                    try:
                        headers = {'Content-type': 'application/json', 'Connection': 'keep-alive'}
                        data['conn'].request('POST', '/api/v1/datapoints', json, headers)
                        res = data['conn'].getresponse()
                        response = res.read()
                        collectd.debug('Response code: %d' % res.status)
                        http_code = res.status
    
                        if res.status == 204:
                            exit_code = True
                            self.samples_sent += 1
                        else:
                            self.reset_connection(data)
                            collectd.error(res.status)
                            if response:
                                collectd.error(response)
                            exit_code = False
                            self.samples_error += 1
    
                    except httplib.ImproperConnectionState, e:
                        self.reset_connection(data)
                        collectd.error('Lost connection to kairosdb server: %s' % e.message)
                        exit_code = False
                        self.samples_error += 1
    
                    except httplib.HTTPException, e:
                        self.reset_connection(data)
                        collectd.error('Error sending http data: %s' % e.message)
                        if response:
                            collectd.error(response)
                        exit_code = False
                        self.samples_error += 1
    
                    except Exception, e:
                        self.reset_connection(data)
                        collectd.error('Error sending http data: %s' % str(e))
                        exit_code = False
                        self.samples_error += 1
            else:
                http_code = 0
                self.samples_dropped += 1
                sent_decision = 'dropped'
                exit_code = True
    
    
            if self.verbose_logging:
                drop_rate = float(0)
                if self.samples_dropped > 0 and self.samples_sent > 1:
                    drop_rate = float(self.samples_dropped) / float(self.samples_sent) * 100
                collectd.info("-> [%s] [delay=%d s / %.2f m / sent=%s s=%d d=%d e=%d drop_rate=%.2f %% ]: writing sample [ http=%d ] [ %s ]" % (datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%m:%S"), ts_diff, ts_diff_m, sent_decision, self.samples_sent, self.samples_dropped, self.samples_error, drop_rate, http_code, json))
    
            return exit_code

    def kairosdb_write(self, values, data=None):
        # noinspection PyBroadException
        try:
            # collectd.info(repr(values))
            if values.type not in self.types:
                collectd.warning('kairosdb_writer: do not know how to handle type %s. do you have all your types.db files configured?' % values.type)
                return

            v_type = self.types[values.type]

            if len(v_type) != len(values.values):
                collectd.warning('kairosdb_writer: differing number of values for type %s' % values.type)
                return

            hostname = values.host.replace('.', self.host_separator)

            tags = self.tags_map.copy()
            if self.add_host_tag:
                tags['host'] = hostname

            plugin = values.plugin
            plugin_instance = ''
            if values.plugin_instance:
                plugin_instance = self.sanitize_field(values.plugin_instance)

            type_name = values.type
            type_instance = ''
            if values.type_instance:
                type_instance = self.sanitize_field(values.type_instance)

            # collectd.info('plugin: %s plugin_instance: %s type: %s type_instance: %s' % (plugin, plugin_instance, type_name, type_instance))

            default_name = self.metric_name % {'host': hostname, 'plugin': plugin,
                                               'plugin_instance': plugin_instance,
                                               'type': type_name,
                                               'type_instance': type_instance}

            if self.pluginsToFormatter and plugin in self.pluginsToFormatter:
                name, tags = self.pluginsToFormatter[plugin].format_metric(self.metric_name, tags, hostname, plugin, plugin_instance, type_name, type_instance)
            elif self.formatter:
                name, tags = self.formatter.format_metric(self.metric_name, tags, hostname, plugin, plugin_instance, type_name, type_instance)
            else:
                name = default_name

            # Remove dots for missing pieces
            name = name.replace('..', '.')
            name = name.rstrip('.')

            # collectd.info('Metric: %s' % name)

            type_list = list(v_type)
            values_list = list(values.values)

            if plugin in self.convert_rates:
                i = 0
                type_list = []
                values_list = []
                for value in values.values:
                    if self.is_counter(v_type[i]):
                        counter = "%s.%s" % (default_name, v_type[i][0])

                        with data['lock']:
                            if value is not None:
                                if counter in self.counters_map:
                                    old_value = self.counters_map[counter]
                                    try:
                                        rate = (value - old_value['value']) / (
                                            values.time - old_value['timestamp'])
                                        values_list.append(rate)
                                        type_list.append(
                                            [v_type[i][0] + '_rate', 'GAUGE', '0',
                                             'U'])
                                    except ZeroDivisionError:
                                        collectd.error(
                                            "Timestamp values are identical (caused divide by error) for %s" + default_name)
                                self.counters_map[counter] = {'value': value, 'timestamp': values.time}
                    else:
                        values_list.append(value)
                        type_list.append(v_type[i])
                    i += 1

            if self.protocol == 'http' or self.protocol == 'https':
                self.kairosdb_write_http_metrics(data, type_list, values.time, values_list, name, tags)
            else:
                self.kairosdb_write_telnet_metrics(data, type_list, values.time, values_list, name, tags)
        except Exception:
            collectd.error(traceback.format_exc())

    @staticmethod
    def is_counter(value_type):
        return value_type[1] == 'DERIVE' or value_type[1] == 'COUNTER'

    def kairosdb_write_telnet_metrics(self, data, types_list, timestamp, values, name, tags):
        tag_string = ""

        for tn, tv in tags.iteritems():
            tag_string += "%s=%s " % (tn, tv)

        lines = []
        i = 0
        for value in values:
            ds_name = types_list[i][0]
            new_name = "%s.%s" % (name, ds_name)
            new_value = value
            collectd.debug("metric new_name= %s" % new_name)

            if new_value is not None:
                line = 'put %s %d %f %s' % (new_name, timestamp, new_value, tag_string)
                collectd.debug(line)
                lines.append(line)

            i += 1

        lines.append('')
        self.kairosdb_send_telnet_data(data, '\n'.join(lines))

    def kairosdb_write_http_metrics(self, data, types_list, timestamp, values, name, tags):
        time_in_milliseconds = timestamp * 1000
        json = '['
        i = 0
        for value in values:
            ds_name = types_list[i][0]
            new_name = "%s.%s" % (name, ds_name)
            new_value = value
            collectd.debug("metric new_name= %s" % new_name)

            if new_value is not None:
                if i > 0:
                    json += ','

                json += '{'
                json += '"name":"%s",' % new_name
                json += '"datapoints":[[%d, %f]],' % (time_in_milliseconds, new_value)
                json += '"tags": {'

                first = True
                for tn, tv in tags.iteritems():
                    if first:
                        first = False
                    else:
                        json += ", "

                    json += '"%s": "%s"' % (tn, tv)

                json += '}'

                json += '}'
            i += 1

        json += ']'

        collectd.debug(json)
        self.kairosdb_send_http_data(data, json, timestamp, name)

    @staticmethod
    def load_plugin_formatters(formatter_directory):
        if os.path.exists(formatter_directory):
            plugins_to_format = {}
            for filename in os.listdir(formatter_directory):
                if filename.endswith(".py"):
                    formatter_name, extension = os.path.splitext(filename)
                    plugin_formatter = imp.load_source(formatter_name, formatter_directory + "/" + filename)
                    for plugin in plugin_formatter.plugins():
                        plugins_to_format[plugin] = plugin_formatter

            return plugins_to_format
        else:
            return {}


writer = KairosdbWriter()
collectd.register_config(writer.kairosdb_config)
collectd.register_init(writer.kairosdb_init)

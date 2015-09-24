from unittest import TestCase
import kairosdb_writer
import datetime
import HttpServer
import collectd
import json


def now():
    return datetime.datetime.now()


class Config:
    def __init__(self, children):
        self.children = children


class Child:
    def __init__(self, key, values):
        self.key = key
        self.values = values


class Values:
    def __init__(self, plugin_type, type_instance, plugin, plugin_instance, host, time, interval, values):
        self.type = plugin_type
        self.type_instance = type_instance
        self.plugin = plugin
        self.plugin_instance = plugin_instance
        self.host = host
        self.time = time
        self.interval = interval
        self.values = values


def setup_config(config):
    c = Config(config)
    kairosdb_writer.kairosdb_config(c)
    kairosdb_writer.kairosdb_init()


CONFIG_DEFAULT = [Child('KairosDBURI', ['http://localhost:8888']),
                  Child('LowercaseMetricNames', ['true']),
                  Child('TypesDB', ['./Types.db']),
                  Child('Tags', ["role=web01", "environment=lab"])
                  ]

CONFIG_RATE = [Child('KairosDBURI', ['http://localhost:8888']),
               Child('LowercaseMetricNames', ['true']),
               Child('TypesDB', ['./Types.db']),
               Child('ConvertToRate',
                     ["interface", "cpu", "mysql_handler", "mysql_qcache"])
               ]

CONFIG_RATE_NO_VALUES = [Child('KairosDBURI', ['http://localhost:8888']),
                         Child('LowercaseMetricNames', ['true']),
                         Child('TypesDB', ['./Types.db']),
                         Child('ConvertToRate', [])
                         ]

CONFIG_INVALID_TAG = [Child('KairosDBURI', ['http://localhost:8888']),
                      Child('LowercaseMetricNames', ['true']),
                      Child('TypesDB', ['./Types.db']),
                      Child('Tags', ["role=web01", "environment"])
                      ]

CONFIG_INVALID_FORMATTER = [Child('KairosDBURI', ['http://localhost:8888']),
                            Child('LowercaseMetricNames', ['true']),
                            Child('TypesDB', ['./Types.db']),
                            Child('Formatter', ['/bogus/BogusFormatter.py'])
                            ]

CONFIG_MISSING_URL = [Child('KairosDBURI', [""]),
                      Child('LowercaseMetricNames', ['true']),
                      Child('TypesDB', ['./Types.db']),
                      Child('Tags', ["role=web01", "environment=lab"])
                      ]

CONFIG_INVALID_URL = [Child('KairosDBURI', ['http//localhost']),
                      Child('LowercaseMetricNames', ['true']),
                      Child('TypesDB', ['./Types.db']),
                      Child('Tags', ["role=web01", "environment=lab"])
                      ]

CONFIG_INVALID_URL_PROTOCOL = [Child('KairosDBURI', ['file//localhost:8888']),
                               Child('LowercaseMetricNames', ['true']),
                               Child('TypesDB', ['./Types.db']),
                               Child('Tags', ["role=web01", "environment=lab"])
                               ]


class TestKairosdbWrite(TestCase):
    """
    Tests for ConvertToRate
    """

    server = None

    @classmethod
    def setUpClass(cls):
        cls.server = HttpServer.HttpServer(8888)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_convertToRate_config_no_value(self):
        """
        Verify that an exception is thrown if no ConvertToRate value
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_RATE_NO_VALUES)
            self.assertTrue(False)
        except Exception as e:
            self.assertEquals(e.message, "Missing ConvertToRate values")

    def test_config_no_value_for_tag(self):
        """
        Verify that an exception is thrown if no value is given for a tag in the config
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_INVALID_TAG)
            self.assertTrue(False)
        except Exception as e:
            self.assertEquals(e.message, "Invalid tag: environment")

    def test_config_invalid_formatter(self):
        """
        Verify that an exception is thrown if no value is given for a tag in the config
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_INVALID_FORMATTER)
            self.assertTrue(False)
        except Exception as e:
            self.assertTrue(e.message.startswith("Could not load formatter /bogus/BogusFormatter.py"))

    def test_init_missing_url(self):
        """
        Verify that an exception is thrown if no KairosDB URL is specified
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_MISSING_URL)
            self.assertTrue(False)
        except Exception as e:
            self.assertEquals(e.message, "KairosDBURI not defined")

    def test_init_invalid_url(self):
        """
        Verify that an exception is thrown if KairosDB URL is a invalid format
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_INVALID_URL)
            self.assertTrue(False)
        except Exception as e:
            self.assertEquals(e.message, "KairosDBURI must be in the format of <protocol>://<host>[:<port>]")

    def test_init_invalid_url_protocol(self):
        """
        Verify that an exception is thrown if KairosDB URL is not a valid protocol
        """
        # noinspection PyBroadException
        try:
            setup_config(CONFIG_INVALID_URL_PROTOCOL)
            self.assertTrue(False)
        except Exception as e:
            self.assertEquals(e.message, 'Invalid protocol specified. Must be either "http", "https" or "telnet"')

    def test_basic(self):
        """
        Verify that the correct values are sent for a metric
        """
        setup_config(CONFIG_DEFAULT)
        values = Values('cpu', 'softirq', 'MycpuMetric', '0', 'localhost', 1442868137, 10.0, [11])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(result[0]['name'], "collectd.MycpuMetric.0.cpu.softirq.value")
        self.assertEquals(result[0]['datapoints'][0][0], 1442868137000)
        self.assertEquals(result[0]['datapoints'][0][1], 11)
        self.assertEquals(result[0]['tags']["host"], "localhost")
        self.assertEquals(result[0]['tags']["role"], "web01")
        self.assertEquals(result[0]['tags']["environment"], "lab")

    def test_not_in_typesDB(self):
        """
        Verify that the type for the metric name does not exist in Types.db
        """
        setup_config(CONFIG_DEFAULT)
        values = Values('foo', 'softirq', 'MycpuMetric', '0', 'localhost', 1442868137, 10.0, [11])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())

        self.assertIsNone(self.server.get_data())

    def test_rate(self):
        """
        Verify that rates are calculated and that the metric name has "_rate" appended to it
        """
        setup_config(CONFIG_RATE)
        values = Values('cpu', 'softirq', 'cpu', '0', 'localhost', 1442868136, 10.0, [10])

        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(result, [])  # First value so can't calculate rate so no data is sent to Kairos

        values = Values('cpu', 'softirq', 'cpu', '0', 'localhost', 1442868137, 10.0, [11])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(len(result),
                          1)  # Verify that the original metric is not sent
        self.assertMetric(result[0], "collectd.cpu.0.cpu.softirq.value_rate",
                          1.0)

        values = Values('cpu', 'softirq', 'cpu', '0', 'localhost', 1442868138, 10.0, [13])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(len(result),
                          1)  # Verify that the original metric is not sent
        self.assertMetric(result[0], "collectd.cpu.0.cpu.softirq.value_rate",
                          2.0)

        #  Not in the rate regex
        values = Values('load', '', 'load_type', '', 'localhost', 1442868138, 10.0, [13, 15, 20])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(len(result),
                          3)  # Verify that the original metric is sent (not a rate)
        self.assertEquals(result[0]['name'], "collectd.load_type.load.shortterm")
        self.assertEquals(result[0]['datapoints'][0][1], 13)
        self.assertEquals(result[1]['datapoints'][0][1], 15)
        self.assertEquals(result[2]['datapoints'][0][1], 20)

    def test_rate_multiple_values(self):
        """
        Verify that rates are calculated and that multiple metrics are sent
        """
        setup_config(CONFIG_RATE)
        values = Values('if_packets', 'eth0', 'interface', '', 'localhost',
                        1442868136, 10.0, [10, 11])

        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(result,
            [])  # First value so can't calculate rate so no data is sent to Kairos

        values = Values('if_packets', 'eth0', 'interface', '', 'localhost',
                        1442868137, 10.0, [11, 13])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertMetric(result[0],
                          "collectd.interface.if_packets.eth0.rx_rate", 1.0)

    def test_rate_mixed_types(self):
        """
        Verify that non-counter metrics are sent and not filtered
        """
        setup_config(CONFIG_RATE)
        values = Values('mysql_qcache', '', 'mysql_qcache', '', 'localhost',
                        1442868136, 10.0, [10, 11, 12, 13, 14])

        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(len(result), 1)  # There is one non-counter value
        self.assertMetric(result[0],
                          "collectd.mysql_qcache.mysql_qcache.queries_in_cache",
                          14)

        values = Values('mysql_qcache', '', 'mysql_qcache', '', 'localhost',
                        1442868137, 10.0, [11, 13, 14, 15, 16])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(len(result), 5)
        self.assertMetric(result[0],
                          "collectd.mysql_qcache.mysql_qcache.hits_rate", 1.0)
        self.assertMetric(result[1],
                          "collectd.mysql_qcache.mysql_qcache.inserts_rate",
                          2.0)
        self.assertMetric(result[2],
                          "collectd.mysql_qcache.mysql_qcache.not_cached_rate",
                          2.0)
        self.assertMetric(result[3],
                          "collectd.mysql_qcache.mysql_qcache.lowmem_prunes_rate",
                          2.0)
        self.assertMetric(result[4],
                          "collectd.mysql_qcache.mysql_qcache.queries_in_cache",
                          16)  # Not a rate

    def test_rate_zero_time_difference(self):
        """
        Verify that rates that have zero time difference don't get reported (prevents divide by zero error)
        """
        setup_config(CONFIG_RATE)
        values = Values('mysql_handler', '', 'mysql_handler', '', 'localhost',
                        1442868136, 10.0, [10])

        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(result,
            [])  # First value so can't calculate rate so no data is sent to Kairos

        values = Values('mysql_handler', '', 'mysql_handler', '', 'localhost',
                        1442868136, 10.0, [11])
        kairosdb_writer.kairosdb_write(values, collectd.get_data())
        result = json.loads(self.server.get_data())

        self.assertEquals(result, [])

    def assertMetric(self, expected, actualName, actualValue):
        self.assertEquals(expected['name'], actualName)
        self.assertEquals(expected['datapoints'][0][1], actualValue)

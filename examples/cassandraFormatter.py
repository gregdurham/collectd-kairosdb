# Adds column family names as tags and removes them from the metric name.
# This was written for use with the FastJMX Collectd plugin that reads JMX metrics from Cassandra.
# NOTE: The code looks for "column_family" as the plugin name and replaces it with "cassandra". In the FastJMX configuration a value can have a "PluginName" property
# which is set to "cassandra" for all metrics except those that have metrics for all column families. These I set to "column_family" as a way to easily
#       identify metrics that this plugin will modify.
# class Formatter:

# For column families, remove plugin_instance from name and change plugin name to "cassandra" and add column_families as a tag
def format(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance):
    if plugin == 'column_family':
        metric_name_template = metric_name_template.replace('%(plugin_instance)s.', '')
        tags['column_family'] = plugin_instance
        plugin = 'cassandra'
    return (metric_name_template % {'host': hostname, 'plugin': plugin, 'plugin_instance': plugin_instance, 'type': type, 'type_instance': type_instance}, tags)

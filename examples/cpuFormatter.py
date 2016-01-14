# Sample formatter for the cpu plugin.
# cpu number and type are set as tags

def plugins():
    return ["cpu"]


def format_metric(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance):
    metric_name_template = metric_name_template.replace('%(plugin_instance)s.', '')
    metric_name_template = metric_name_template.replace('%(type)s.', '')
    tags['cpu'] = plugin_instance
    tags['type'] = type_instance
    type_instance = 'utilization'

    return metric_name_template % {'host': hostname, 'plugin': plugin, 'plugin_instance': plugin_instance, 'type': type, 'type_instance': type_instance}, tags

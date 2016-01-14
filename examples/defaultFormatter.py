# Sample default formatter
# Disk and interface (network) plugin metrics names are set along with tags

def format_metric(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance):
    if plugin == 'disk':
        metric_name_template = metric_name_template.replace('%(plugin_instance)s.', '')
        tags['disk'] = plugin_instance

    if plugin == 'interface':
        metric_name_template = metric_name_template.replace('%(type_instance)s', '')
        tags['interface'] = type_instance

    return metric_name_template % {'host': hostname, 'plugin': plugin, 'plugin_instance': plugin_instance, 'type': type, 'type_instance': type_instance}, tags

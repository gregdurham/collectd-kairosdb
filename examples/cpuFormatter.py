# Formatter for cpu plugin.
# cpu number and type are set as tags
# class Formatter:

def format(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance):
	if plugin == 'cpu':
		metric_name_template = metric_name_template.replace('%(plugin_instance)s.', '')
		metric_name_template = metric_name_template.replace('%(type)s.', '')
		tags['cpu'] = plugin_instance
		tags['type'] = type_instance
		type_instance = 'utilization'
	
	if plugin == 'disk':
		metric_name_template = metric_name_template.replace('%(plugin_instance)s.', '')
		tags['disk'] = plugin_instance
		
	if plugin == 'interface':
		metric_name_template = metric_name_template.replace('%(type_instance)s', '')
		tags['interface'] = type_instance
		
	return (metric_name_template % {'host': hostname, 'plugin': plugin, 'plugin_instance': plugin_instance, 'type': type, 'type_instance': type_instance}, tags)

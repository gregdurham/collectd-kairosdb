def plugins():
    return ["a", "b", "c", "d"]

def format(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance):
    return "metric1Formatter", {"tag1": "a", "tag2": "b"}
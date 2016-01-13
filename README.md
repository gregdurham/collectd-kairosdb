collectd-kairosdb
================

A [KairosDB](https://code.google.com/p/kairosdb/) plugin for [collectd](http://collectd.org) using collectd's [Python plugin](http://collectd.org/documentation/manpages/collectd-python.5.shtml). 

This is based on the [collectd-carbon](https://github.com/indygreg/collectd-carbon) plugin

Install
-------
 1. Place kairosdb_writer.py in /usr/lib64/collectd/ (assuming you have collectd installed to /usr/lib64/collectd/).
 2. Configure the plugin (see below).
 3. Restart collectd.

Configuration
-------------
Add the following to your collectd config **or** use the included kairosdb.conf.

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        ModulePath "/usr/lib64/collectd/"

        Import "kairosdb_writer"

        <Module "kairosdb_writer">
            KairosDBURI "telnet://localhost:4242"
            LowercaseMetricNames true
            TypesDB "/usr/share/collectd/types.db" "/etc/collectd/types/custom.db"
            ConvertToRate "interface", "cpu"
        </Module>
    </Plugin>
    

### Properties
*AddHostTag* - adds a host tag if true. True by default.   

*Formatter* - the full path to a formatter.  See the Formatters section below.

*HostSeparator* - separator character used between host name parts. Defaults to underscore("_").  
  
*LowercaseMetricNames* - lower cases the metric name if true. Defaults to false.  

*KairosDBURI* - URI for the Kairos host, must be in the form <protocol>://<host>[:<port>].  Protocol may be one of (telnet, http, https). Required.   

*TypesDB* - Data-set specifications. See [Types.db](https://collectd.org/documentation/manpages/types.db.5.shtml). 
 
*MetricName* - the name of the metric. This is built using pre-defined variables. See [Naming Schema](https://collectd.org/wiki/index.php/Naming_schema) for information about these variables. 
  For example, if the metric name is set to "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.otherstuff", this will produce a metric name that looks like this 
  "collectd.processes.ps_state.blocked.value.otherstuff". The pre-defined variables are *host*, *plugin*, *plugin_instance*, *type*, and *type_instance*. The default is "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.%(type_instance)s".
    
*MetricSeparator* - separator character used between metric name parts. Defaults to a period(".").

*ConvertToRate* - converts COUNTER and DERIVE values to rates for the listed plugins. This is a comma delimited list of plugin names. The counter values are suppressed and a new metric containing the rate is sent to KairosDB. The name for rates will contain "_rate" on the end of the name.
     
*Tags* - KairosDB tags to send. At least one tag is required. The host name is added as a tag by default unless AddHostTag is set to false. For example, "customer=acme"


### Formatters
Formatters provide a way to customize the metric name or tags. A formatter is a python script that has a format function. See the ./examples/defaultFormatter.py for an example of a default formatter.
See the ./examples/cpuFormatter.py for an example of a plugin formatter.
There are two ways to create formatters.

 1. Default Formatter - The "Formatter" property let's you specify the location of a single formatter that will be called for all plugins.  
 2. Plugin Formatters - Formatters that applies to a specific list of plugins can be created. These formatters are loaded from the "formatters" subdirectory where kairosdb_writer.py exists. 
 
Formatters are used in the following way.

 When the writer is first loaded the default formatter and the plugin formatters are loaded. If the "Formatter" property exists, the default formatter is loaded from the specified location. 
 All plugin formatter files that have a .py extension found in the "formatters" directory are loaded.
 
 When the writer is called with values for a plugin then
 
 1. If a plugin formatter exists for the plugin, its format function is called and the default formatter is not called.
 2. If no plugin formatter is found and the default formatter exists then its format function is called. 
 
#### Formatter Functions
Both the default formatter and specific plugin formatters must have a format function with the following signature. It returns the metric name and a dictionary of tags (tag name/value).

    format(metric_name_template, tags, hostname, plugin, plugin_instance, type, type_instance)
    
Plugin formatters must also include a plugins function which is called when the writer is loaded. This returns a list of plugin names that this formatter applies to.

    plugins()






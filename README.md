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
        </Module>
    </Plugin>
    

### Properties
**AddHostTag** - adds a host tag if true. True by default.  
**Formatter** - the full path to a formatter. A formatter is python code used to modify the metric name and/or the tags. The formatter must contain a function named
  "format". It takes the metric name as specified in this file, the tags, hostname, plugin, plugin_instance, type, and type_instance and returns the metric name and the tags. 
  A formatter could be used to pull out of the metric name something that should be a tag. See the ./examples/cassandraFormatter.py for an example.
**HostSeparator** - separator character used between host name parts. Defaults to underscore("_").    
**LowercaseMetricNames** - lower cases the metric name if true. Defaults to false.  
**KairosDBURI** - URI for the Kairos host, must be in the form <protocol>://<host>:<port>.  Protocol may be one of (telnet, http, https). Required.   
**TypesDB** - ???  
**MetricName** - the name of the metric. This is built using pre-defined variables. See [Naming Schema](https://collectd.org/wiki/index.php/Naming_schema) for information about these variables. 
  For example, if the metric name is set to "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.otherstuff", this will produce a metric name that looks like this 
  "collectd.processes.ps_state.blocked.value.otherstuff". The pre-defined variables are *host*, *plugin*, *plugin_instance*, *type*, and *type_instance*. The default is "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.%(type_instance)s".  
**MetricSeparator** - separator character used between metric name parts. Defaults to a period(".").     
**Tags** - KairosDB tags to send. At least one tag is required. The host name is added as a tag by default unless AddHostTag is set to false. For example, "customer=acme"






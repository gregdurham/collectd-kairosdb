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
            KairosDBHost "localhost"
            KairosDBPort 4242
            KairosDBProtocol "telnet"
            LowercaseMetricNames true
            TypesDB "/usr/share/collectd/types.db" "/etc/collectd/types/custom.db"
        </Module>
    </Plugin>
    

### Properties
**AddHostTag** - adds a host tag if true. True by default.  
**HostSeparator** - separator character used between host name parts.  
**LowercaseMetricNames** - lower cases the metric name if true.  
**KairosDBHost** - host name or IP address of KairosDB server.  
**KairosDBPort** - KairosDB server port.  
**KairosDBProtocol** - specifies how the metrics are sent to KairosDB. The options are TELNET or HTTP.  
**TypesDB** - ???  
**MetricName** - the name of the metric. This is built using pre-defined variables. See [Naming Schema](https://collectd.org/wiki/index.php/Naming_schema) for information about these variables. 
  For example, if the metric name is set to "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.otherstuff", this will produce a metric name that looks like this 
  "collectd.processes.ps_state.blocked.value.otherstuff". The pre-defined variables are *host*, *plugin*, *plugin_instance*, *type*, and *type_instance*. The default is "collectd.%(plugin)s.%(plugin_instance)s.%(type)s.%(type_instance)s".  
**MetricSeparator** - separator character used between metric name parts.     
**Tags** - KairosDB tags to send  





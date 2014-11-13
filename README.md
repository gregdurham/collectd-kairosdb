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
            KairosDBProtocol "tcp"
            LowercaseMetricNames true
            TypesDB "/usr/share/collectd/types.db" "/etc/collectd/types/custom.db"
        </Module>
    </Plugin>
    

### Properties
     KairosDBHost - host name or IP address of KairosDB server.
     KairosDBPort - KairosDB server port.
     TypesDB - ???
     LowercaseMetricNames - lower cases the metric name if True.
     MetricPrefix - prefix of the metric name.
     HostPostfix - appended to the hostname as part of the metric name.
     HostSeparator - separator character used between host name parts.
     MetricSeparator - separator character used between metric name parts. 
     KairosDBProtocol - how the metrics are sent to KairosDB. The options are TELNET or HTTP.
     Tags - KairosDB tags to send
     MetricName - collectd.%(hostname)s.%(metric)s.%(type)s.otherstuff
   





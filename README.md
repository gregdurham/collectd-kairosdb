collectd-logster
================

A [KairosDB](https://code.google.com/p/kairosdb/) plugin for [collectd](http://collectd.org) using collectd's [Python plugin](http://collectd.org/documentation/manpages/collectd-python.5.shtml). 

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



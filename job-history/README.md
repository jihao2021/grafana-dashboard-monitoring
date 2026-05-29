## Job History Dashboard


![job history](/images/job-history-dashboard.png)

Data is collected from `sacct` and saved into influxdb (only compatible with 1.x). Similar to XDMoD but can do a few nifty things like track historical GPU usage.

Dashboard is still a work in progress but is available on hpc-grafana



### Setup

The script reads from a `.env` file for influxdb configuration. A template is provided but not filled in for security reasons:

```
INFLUXDB_HOST="hostname"
INFLUXDB_PORT="8086"
INFLUXDB_DATABASE="dbname"
INFLUXDB_USERNAME="username"
INFLUXDB_PASSWORD="password"
```

Currently works for Influxdb 1.x

For continuous monitoring it will need to be called periodically. Can be done as cronjob. The script will need access to `sacct` and databases for both Discovery and Endeavour clusters





## Slurm Node Utilization Dashboard

Collects data from `scontrol show node` and writes it to influxdb database.

![dashboard screenshot](/images/slurm-node-utilization-overview.png)


Data for each node is displayed and grouped by partition. It shows:

* Node state (Allocated, Idle, Planned, Mixed)
* Utilization in terms of allocated vs total (CPU and Memory)
* Utilization in terms of GPU, grouped by GPU type

![gpu screenshot](/images/gpu-utilization.png)


By default data from Discovery cluster is collected but there is a `--condo` option for the Endeavour/condo cluster.
There are 2 json files the represent dashboards for each cluster. They are separate so the discovery one can be made public (if desired) and so the Endeavour one can show different information on gpu ownership.

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

For continuous monitoring it will need to be called periodically. Can be done as cronjob. The script will need access to `scontrol` and databases for both Discovery and Endeavour clusters





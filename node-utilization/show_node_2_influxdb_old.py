import json, argparse, subprocess
from time import time, sleep, strftime
from influxdb import InfluxDBClient
from dotenv import load_dotenv
import os

# Only compatible with influxdb 1.x


# read influxdb config from .env file
load_dotenv()
host     = os.getenv("INFLUXDB_HOST")
port     = os.getenv("INFLUXDB_PORT")
database = os.getenv("INFLUXDB_DATABASE")
username = os.getenv("INFLUXDB_USERNAME")
password = os.getenv("INFLUXDB_PASSWORD")


client = InfluxDBClient(
    database=database,
    host=host,
    port=port,
    username=username,
    password=password
    )

parser = argparse.ArgumentParser(description='Run scontrol show node, save data to influxdb')
parser.add_argument('--condo','-c', action='store_true',
    help='request data from condo cluster')

args=parser.parse_args()

# We are collecting scontrol show node data and writing it to influxdb

show_node_string=["scontrol","show","node","--json"]


# Option for condo nodes too
if args.condo:
    show_node_string+=['--cluster',' condo']

show_node_data=subprocess.run(show_node_string,
    text=True,
    capture_output=True)

current_time=strftime("%Y-%m-%dT%H:%M:%S%Z")

data=json.loads(show_node_data.stdout)




# Information of interest
keys=['name','state','partitions','alloc_cpus','cpus','alloc_memory','real_memory','gres','gres_used']

# Use the following as a 'tag'
# state - A node can be in multiple states, Allocated+Drain, Idle+Planned, ....
#       - Primary states are, Down, Idle, Allocated, Mixed
#       - Secondary states are not used in dashboard but could be interesting to look at  
# partition
# gres/gpu model - for tracking what gpus were requested and allocated, what's available

primary_states=['MIXED','ALLOCATED','IDLE','DOWN']
secondary_states=['PLANNED','DRAIN',
'NOT_RESPONDING','RESERVED','COMPLETING']


node_id=0


# This loop parses the scontrol show node info in json format and
# builds an influxdb data point for each node, then writes to db
for node in data['nodes']:
#    print(node_id)
#    for key in keys:
#        print(node[key],end=', ')
#    print('')
    point = [{}]
    point[0]['measurement']='scontrol_show_node'
    #point[0]['time']=current_time
    tags = {}
    fields={}
    if args.condo:
        tags['cluster'] = 'condo'
    else:
        tags['cluster'] = 'discovery'
    for key in keys:
        #print(key)
        #print(node[key],end=' ')
    #print('')
        if key=='state':
            for pstate in primary_states:
                if pstate in node[key]:

                    
                    #point[0]['primary_state']=pstate
                    #fields['primary_state']=pstate
                    tags['primary_state']=pstate
            for sstate in secondary_states:
                if sstate in node[key]:
                    sstate_list=node[key][1:]
                    #point.tag('secondary_state',",".join(sstate_list))
                    tags['secondary_state']=",".join(sstate_list)

                    break

            #print(point)
        elif key=='partitions':
            partition=",".join(node[key])
            #point.tag(key,partition)
            tags[key]=partition
            continue
        elif key=='gres':
            gres_data=node[key].split(':')
            if len(gres_data) > 1:
                tags['gres_type'] = gres_data[1]
                fields[key] = int(gres_data[2].split("(")[0])
            else:
                tags['gres_type'] = 'none'
                fields[key]        = 0
        elif key=='gres_used':
            used_gres_data=node[key].split(':')
            if len(used_gres_data) > 1:
                used_gres_quantity=int(used_gres_data[2].split("(")[0])
                fields[key] = used_gres_quantity
            else:
                fields[key] = 0
        elif key=='name':
            fields[key]=node[key]
            fields['node_id']=node_id
            node_id+=1
        else:
            fields[key] = node[key]
    tags['debug']=False
    point[0]['fields']=fields
    state=client.write_points(point,tags=tags)

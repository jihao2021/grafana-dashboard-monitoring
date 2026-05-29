from tqdm import tqdm
import json, argparse, subprocess, time
from influxdb import InfluxDBClient 
from influxdb.exceptions import InfluxDBClientError
from dotenv import load_dotenv
import os

# Only compatible with influxdb 1.x


# Read json data from sacct and flatten fields
def json2dict(a, input_dict, key_prefix_string=""):
    if key_prefix_string == "":
        prepend = ""
    else:
        prepend = key_prefix_string+'.'
    if type(a) == str:
        #print(f"Key is {prepend}{a} and value is {a}\n")
        return
    for key, value in a.items():
        if key == 'steps':
        #    print('skipping steps')
            continue
        if key == 'tres':
            for tres_key, tres_value in value.items():
                for tres_type in tres_value:
                    if tres_type['name'] == "":
                        name_string = ""
                    else:
                        name_string = "."+tres_type['name']
                    key_name = f"{prepend}{key}.{tres_key}.{tres_type['type']}{name_string}"
                    out_value = f"{tres_type['count']}"
                    #print(f"Key is {key_name} and value is {out_value}\n")
                    input_dict.update({key_name: out_value})
            return
        if type(value) == dict:
            json2dict(value, input_dict, prepend+key)
        elif type(value) == list:
            [json2dict(item, input_dict, prepend+key) for item in value]
        else:
            if value == "":
                value = None
            key_name = f"{prepend}{key}"
            #print(f"Key is {key_name} and value is {value}\n")
            input_dict.update({key_name: value})


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

parser = argparse.ArgumentParser(description='Run sacct, save data to influxdb')
parser.add_argument('--condo','-c', action='store_true',
    help='request data from condo cluster')
parser.add_argument('--date','-d',
    help='Date to request sacct data YYYY-MM-DD')

args=parser.parse_args()



# Determine date to collect data from
# default is for "yesterday"

if args.date==None:
    date_in_seconds = time.mktime(time.localtime())-86400
else:
    try:
        date_struct = time.strptime(args.date,'%Y-%m-%d')
    except ValueError:
        print(f"Incorrect format for date: {args.date}")
        sys.exit(1)
    date_in_seconds = time.mktime(date_struct)


the_day_before_in_seconds = date_in_seconds - 86400

date_string = time.strftime("%Y-%m-%d",time.localtime(date_in_seconds))
the_day_before_string = time.strftime("%Y-%m-%d",time.localtime(the_day_before_in_seconds))



# We are collecting sacct data and writing it to influxdb
sacct_string=f"sacct -a -E {date_string} -S {the_day_before_string} --json".split(" ")



# Option for condo nodes too
if args.condo:
    sacct_string+=['--cluster',' condo']

print(f"Retrieving job data for {date_string}...")
sacct_data=subprocess.run(sacct_string,
    text=True,
    capture_output=True)
#sacct_data = open('job_log.json','r')

print("Parsing job data...")
data = json.loads(sacct_data.stdout)




last_time=0
last_tags={}
time_counter=0

# This loop parses job data from sacct in dictionary format
# each job is a point
for single_job in tqdm(data["jobs"]):
    #print(f"Ingesting job {counter}")
    job_dict = {}
    json2dict(single_job, job_dict)

    point  = [{}]
    point[0]['measurement'] = 'sacct_data'
    tags   = {}
    fields = {}

    #point[0]['time'] = start_time

    for key, value in job_dict.items():
        # find tags
        if 'tres.requested.gres.gpu:' in key:
            tag_name,gpu_type = key.split(':')
            #point.tag('requested_gpu',gpu_type)
            tags['requested_gpu']=gpu_type
            #print(key)
        if 'tres.allocated.gres.gpu:' in key:
            tag_name,gpu_type = key.split(':')
            #point.tag('allocated_gpu',gpu_type)
            tags['allocated_gpu']=gpu_type
            #print(f'allocated -tag:{tag_name}\tgpu_type:{gpu_type}')
        if key=='partition':
            #point.tag(key,value)
            tags[key]=value
            continue
        # do this after tags have been set
        # influxdb will overwrite a point if new point has same time
        # time is determined by time.submission
        if key=='time.submission':
            time_us=value*1000*1000
            if value==last_time and last_tags==tags:
                time_counter+=1
                time_us+=(time_counter%1000000)
        #        print(f"overwrite possible: {value} {time_counter}")
            last_tags=tags.copy()
            last_time=value
            point[0]['time'] = time_us
        if 'signal' in key:
            fields[key] = value
            continue
        try:
            if value.isdigit() and key != "name":
                value=int(value)
        except AttributeError:
            "isdigit() cannot be called on value, it's probably fine/?"
        except ValueError:
            value=float(value)
        fields[key] = value
        #point.field(key, value)

    tags['debug']      = True
    point[0]['fields'] = fields
    #print(point[0]['fields']['derived_exit_code.signal.name'])
    try:
        state = client.write_points(point,tags=tags,time_precision="u")
        #1+1
    except InfluxDBClientError as e:
	#print("rest api exception!!")
        print(f"Error message: {e.message}")
        print(f"Body: {e.body}")
        print(f"HTTP response status: {e.status}")
print("all_jobs_written")

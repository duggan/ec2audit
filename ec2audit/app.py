from os import environ
from os.path import join
from boto import ec2, dynamodb

from ec2audit.utils import *
from ec2audit.output import to_dir, to_stdout

def name_and_tags(it):
    name = it.tags.get('Name') or it.id

    tags = it.tags.copy();
    tags.pop('Name')
    return name, NaturalOrderDict(tags)

def instance_data(i):
    data = NaturalOrderDict()

    verbatim = ['id', 'image_id', 'architecture', 'instance_type',
                'launch_time', 'placement', 'private_ip_address', 'ip_address',
                'root_device_type', 'state']

    vpc_only = ['sourceDest', 'subnet_id', 'vpc_id']

    for key in verbatim:
        v = i.__dict__[key]
        if v == '' or v == None: # but not False
            continue
        data[key] = v

    if i.__dict__.get('vpc_id'):
        for key in vpc_only:
            data[key] = i.__dict__[key]

    data['security_groups'] = NaturalOrderDict()
    for group in i.groups:
        data['security_groups'][group.id] = group.name

    if i.block_device_mapping:
        data['devices'] = NaturalOrderDict()
        for dev, vol in i.block_device_mapping.items():
            data['devices'][dev] = vol.volume_id

    name, tags = name_and_tags(i)
    if tags:
        data['tags'] = tags

    tags = i.tags.copy();
    tags.pop('Name')
    if tags:
        data['tags'] = NaturalOrderDict(tags)

    return name, data


def get_ec2_instances(econ):
    instances = NaturalOrderDict()
    for res in econ.get_all_instances():
        for i in res.instances:
            name, data = instance_data(i)
            instances[name] = data

    return instances


def run(params):
    access_key, secret_key = get_aws_credentials(params)
    region = params['<region>']
    if params['--format'] not in ['j', 'y', 'p', 'json', 'yaml', 'pprint']:
        exit_with_error('Error: format must be one of json or yaml\n')

    con = ec2.connect_to_region(region,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key)


    instances = get_ec2_instances(con)
    output = params['--output']
    if not output:
        to_stdout(instances, params['--format'])
    else:
        to_dir(instances, params['--format'], output)
""" Lambda function - check ec2 """
from datetime import (
    datetime,
    timedelta
)
import boto3

def get_ec2_last_metric(instance_id, metric_name, stat_type, unit_type):
    """Get ec2 metrics"""
    cw_client = boto3.client('cloudwatch')
    msg = ""
    metrics_data = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName=metric_name,
        StartTime=datetime.utcnow() - timedelta(seconds=600),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=[stat_type],
        Unit=unit_type,
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance_id
            },
        ],
    )
    for datapoints in metrics_data['Datapoints']:
        if not datapoints['Unit'] == 'Count':
            msg = "{} {} is {} {}".format(
                stat_type,
                metric_name,
                round(datapoints[stat_type], 2),
                datapoints['Unit']
            )
        else:
            msg = "{} {} is {}".format(
                stat_type,
                metric_name,
                round(datapoints[stat_type], 2)
            )
    return msg

def subnet_id_to_name(s_id):
    """ Translate Subnet id to name """
    ec2 = boto3.client('ec2')
    get_subnet = ec2.describe_subnets(SubnetIds=[s_id])
    for subnet in get_subnet['Subnets']:
        for name_tag in subnet['Tags']:
            if name_tag['Key'] == 'Name':
                msg = "{}".format(name_tag['Value'])
                return msg
    msg = s_id
    return msg

def vpc_id_to_name(v_id):
    """ Translate VPC id to name """
    ec2 = boto3.client('ec2')
    get_vpc = ec2.describe_vpcs(VpcIds=[v_id])
    for vpc in get_vpc['Vpcs']:
        for name_tag in vpc['Tags']:
            if name_tag['Key'] == 'Name':
                msg = "{}".format(name_tag['Value'])
                return msg
    msg = v_id
    return msg


# Main function
def cloud_control_check_ec2(event, context):
    """ Lambda function - check ec2 """

    # validate instance name
    #ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [event["body"]["InstanceName"]]
            }
        ]
    )
    instance = []
    instance_list = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_list.append(instance['InstanceId'])

    if not instance_list:
        msg = "I cannot find the instance with name {}.".format(event["body"]["InstanceName"])
        return {"msg": msg}

    #ec2_instance = ec2.instances.filter(InstanceIds=instance_list)

    msg = ""
    if event["body"]["CheckType"] == 'all':
        msg = "Here are the information about instance {}. ".format(
            event["body"]["InstanceName"]
        )
    if event["body"]["CheckType"] == 'type' or event["body"]["CheckType"] == 'all':
        msg = "{} The type of the instance is {}.".format(msg, instance['InstanceType'])
    if event["body"]["CheckType"] == 'security group' or event["body"]["CheckType"] == 'all':
        secgroup = []
        for enis in instance['NetworkInterfaces']:
            for sgs in enis['Groups']:
                secgroup.append(sgs['GroupName'])
            if len(secgroup) == 1:
                temp_msg = "Security group attached to the instance is {}.".format(secgroup)
            else:
                temp_msg = "Security groups attached to the instance are {}.".format(secgroup)
        msg = "{} {}".format(msg, temp_msg)
    if event["body"]["CheckType"] == 'availability zone' or event["body"]["CheckType"] == 'all':
        msg = "{} Instance is located in {} availability zone. ".format(
            msg, instance['Placement']['AvailabilityZone']
        )
    if event["body"]["CheckType"] == 'subnet' or event["body"]["CheckType"] == 'all':
        # logic for taking name of vpc and subnet, instead of id
        subnet_name = subnet_id_to_name(instance['SubnetId'])
        vpc_name = vpc_id_to_name(instance['VpcId'])
        msg = "{} Subnet is {}, and exists in VPC {}. ".format(msg, subnet_name, vpc_name)
    if event["body"]["CheckType"] == 'status' or event["body"]["CheckType"] == 'all':
        msg = "{} Instance is in {} state.".format(msg, instance['State']['Name'])
    if event["body"]["CheckType"] == 'key pair' or event["body"]["CheckType"] == 'all':
        if 'KeyName' in instance:
            msg = "{} {} key pair is attached to this instance.".format(msg, instance['KeyName'])
        else:
            msg = "{} No key pair is attached to this instance.".format(msg)
    if event["body"]["CheckType"] == 'cpu' or event["body"]["CheckType"] == 'all':
        temp_msg = get_ec2_last_metric(
            instance['InstanceId'],
            'CPUUtilization',
            'Average',
            'Percent'
        )
        msg = "{} {}.".format(msg, temp_msg)
    if event["body"]["CheckType"] == 'network' or event["body"]["CheckType"] == 'all':
        temp_msg = get_ec2_last_metric(instance['InstanceId'], 'NetworkIn', 'Average', 'Bytes')
        msg = "{} Last network trasfers: {}, ".format(msg, temp_msg)
        temp_msg = get_ec2_last_metric(instance['InstanceId'], 'NetworkOut', 'Average', 'Bytes')
        msg = "{} and {}. ".format(msg, temp_msg)
    if event["body"]["CheckType"] == 'fail' or event["body"]["CheckType"] == 'all':
        temp_msg = get_ec2_last_metric(
            instance['InstanceId'],
            'StatusCheckFailed',
            'Average',
            'Count'
        )
        msg = "{} Fails: {}. ".format(msg, temp_msg)
    return {"msg": msg}

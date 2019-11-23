import boto3
import json
import time
import requests
from paramiko import SSHClient, SFTPClient
import paramiko
from botocore.exceptions import ClientError

VL = 5
deleteEnable = False

global ec2
ec2 = boto3.resource('ec2')

def createKey():
    global ec2
    

    key_pair = ec2.create_key_pair(KeyName='toranja-script')

    KeyPairOut = str(key_pair.key_material)

    with open('key.pem','w') as file:
        file.write(KeyPairOut)

def createLoadBalancer(SecurityGroup, name = 'LoadBalancerToranjaScript'):
    client = boto3.client('elb')
    response_deleted = client.delete_load_balancer(
        LoadBalancerName=name
    )

    response = client.create_load_balancer(
        LoadBalancerName=name,
        Listeners=[
            {
                'Protocol': 'HTTP',
                'LoadBalancerPort': 80,
                'InstanceProtocol': 'HTTP',
                'InstancePort': 5000,
            }
        ],
        AvailabilityZones=[
            'us-east-1a','us-east-1b','us-east-1c', 'us-east-1e', 'us-east-1f', 'us-east-1d'
        ],
        SecurityGroups=SecurityGroup,
        Tags=[
            {
                'Key':'Owner',
                'Value': 'Bruno'
            },
        ]
    )
    return name, response


def getAvaliabilityZones():
    client = boto3.client('ec2')
    return client.describe_availability_zones()
def createAutoScale(Instance_id, name='ToranjasScaling', name_load = 'LoadBalancerToranjaScript'):
    client = boto3.client('autoscaling')
    response = client.create_auto_scaling_group(
        AutoScalingGroupName=name,
        InstanceId=Instance_id,
        MinSize=1,
        MaxSize=10,
        HealthCheckGracePeriod=300,
        LoadBalancerNames=[
            name_load,
        ]
    )
    return response


def createSecurityGroup(name = 'default', ports = [22]):
    ec2 = boto3.client('ec2')
    rules = []
    for i in ports:
        rules.append({'IpProtocol': 'tcp',
                'FromPort': i,
                'ToPort': i,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]})


    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    try:
        response = ec2.create_security_group(GroupName=name,
                                            VpcId=vpc_id,
                                            Description="Created by toranjascript")
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

        data = ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=rules)
        print('Ingress Successfully Set %s' % data)
    except ClientError as e:
        print(e)
        return e
    return security_group_id


def createInstance(userdata = None, type = 'default', security_group = 'falafou'):

    ec2 = boto3.resource('ec2')

    if (userdata == None):
        instances = ec2.create_instances(
            ImageId='ami-04b9e92b5572fa0d1',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName='toranja-script',
            TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': 'Bruno'
                    },
                    {
                        'Key': 'Type',
                        'Value': 'VPN'
                    },
                ]
            },
            ]
        )
    else:
        instances = ec2.create_instances(
            ImageId='ami-04b9e92b5572fa0d1',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName='toranja-script',
            SecurityGroups=[security_group],
            UserData=userdata,
            TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': 'Bruno'
                    },
                    {
                        'Key': 'Type',
                        'Value': type
                    },
                ]
            },
            ]
        )


    
    return [[instance.public_ip_address, instance.id] for instance in instances]



def startAndGetIp(cloud_init, tag, security_group):
    if (VL > 0):
        print("Start.    launching instance ... " + tag)
    instances = createInstance(cloud_init, tag, security_group)
    response = ec2.Instance(instances[0][1])
    while (response.public_ip_address == None):
        response = ec2.Instance(instances[0][1])
    if (VL > 2):
        print("Info.     Instance ip :  " + response.public_ip_address)
        print("Info.     Instance id :  " + instances[0][1])
    ip = response.public_ip_address
    return ip, instances[0][1]

def checkState(id):
    response = ec2.Instance(id)
    if (VL > 2):
        print("Check.    " + id + " state is ... ", end="")
    while (response.state['Code'] != 16):
        response = ec2.Instance(id)
        print(response.state['Name'])
        time.sleep(5)
    print("Done.     ready id: " + id)
    
    

def checkServer(ip):
    if (VL > 2):
        print("Info.     generating OpenVpn configs")
        print("Check.    waiting for VPN on: " + ip, end="")
    try:
        r = requests.get(url = "http://" + ip)
    except:
        r = None
    while (r==None or r.status_code != 200):
        print(".", end='', flush=True)
        try:
            r = requests.get(url = "http://" + ip)
        except:
            r = None
        time.sleep(5)
    print("\nDone.     server up on " + ip)
    return 
    

def SFTP_script(ip, dire, origi, dest):
    
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
    t = client.get_transport()
    sftp = SFTPClient.from_transport(t)
    
    if (dire == 1):
        
        for i in range(len(dest)):
            if (VL > 4):
                print("Get.  Getting files(" + origi[i] + ") from " + ip)
            sftp.get(origi[i], dest[i])
    else:
        for i in range(len(dest)):
            if (VL > 4):
                print("Send.     Sending files(" + origi[i] + ") to " + ip)
            sftp.put(origi[i], dest[i])

def startVpnSerrion(ip, file):
    for i in range(len(ip)):
        if (VL > 3):
            print("Start.    Starting VPN session on " + ip[i])
        SFTP_script(ip[i], 0, [file[i]], ['/home/ubuntu/openvpn_client.conf'])
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip[i], port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
        client.exec_command("openvpn" ) #TODO: check openvpn, separete in a external script, configure init.d script
        client.exec_command("sudo tmux new -d -s vpn 'openvpn --config /home/ubuntu/openvpn_client.conf;'" )
        client.exec_command("sudo cp /var/lib/cloud/instances/*/user-data.txt /home/ubuntu/user-data.txt;" )
        client.exec_command("echo \' \' >> /home/ubuntu/user-data.txt;" )
        client.exec_command("echo \'echo \"' >> /home/ubuntu/user-data.txt;" )
        client.exec_command("cat /home/ubuntu/openvpn_client.conf >> /home/ubuntu/user-data.txt;" )
        client.exec_command("echo \'\" >> openvpn.config\' >> /home/ubuntu/user-data.txt;" )
        
        if (VL > 3):
            print("Done.     VPN session started on " + ip[i])

def deleteAutoScalingLaunchConfig(name = 'ToranjasScaling'):
    client = boto3.client('autoscaling')
    
    
    try:
        response = client.delete_auto_scaling_group(
            AutoScalingGroupName=name,
            ForceDelete=True
        )
    except:
        response = ""
        pass
    
    try:
        response_launch_config = client.delete_launch_configuration(
            LaunchConfigurationName='ToranjasScaling'
        )
    except:
        response_launch_config = ""
        pass

    
    
    return response, response_launch_config


def createCloudInitWithOpenVpn(customCommands = [], outName = "custom_cloud_init.sh", openvpnFile="openvpn_clients/serverless.ovpn", inName = None ):
    if (VL > 3):
            print("Start.    Creating cloud-init file for " + openvpnFile)
    needAppend=[]
    if (inName != None):
        with open(inName, 'r') as file:
            for line in file:
                needAppend.append(line)
    if (len (customCommands)!=0):
        needAppend.append('#!/bin/bash\n')
        for i in customCommands:
            needAppend.append(i)
    needAppend.append("\n")
    needAppend.append("echo \"")

    with open(openvpnFile, 'r') as file:
        for line in file:
            needAppend.append(line)

    needAppend.append("\" >> /home/ubuntu/openvpn.config")
    needAppend.append("\nsudo tmux new -d -s vpn 'openvpn --config /home/ubuntu/openvpn.config;'")

    with open(outName, 'w') as file:
        for line in needAppend:
            file.write(line)

    if (VL > 3):
            print("Done.    Done cloud-init file for " + openvpnFile + " saved as " + outName)
    return outName

    
def getSecurityGroupId(name = 'autoscaling'):
    client = boto3.client('ec2')
    response = client.describe_security_groups(
        GroupNames=[
            name,
        ]
    )

    return response


try:
    createKey()
except:
    print("Already have a key toranja-script, delete manually if needed")

if True:
    deleteAutoScalingLaunchConfig()

try:
    security_group_id = createSecurityGroup('vpn', [22, 80, 1194])
except:
    pass


openvpn_ip, instance_openvpn = startAndGetIp('''#!/bin/bash
    wget -O - https://raw.githubusercontent.com/brunoartc/openvpn-init-script/master/openvpn.sh | bash''', 'vpn', 'vpn')


checkServer(openvpn_ip)




SFTP_script(openvpn_ip, 1, ["/home/ubuntu/openvpn/clients/database.ovpn", "/home/ubuntu/openvpn/clients/serverless.ovpn"], ["./openvpn_clients/database.ovpn", "./openvpn_clients/serverless.ovpn"])

createCloudInitWithOpenVpn(customCommands = ["wget -O - https://raw.githubusercontent.com/brunoartc/cloud_database/master/ec2.sh | bash"], openvpnFile = "openvpn_clients/database.ovpn")

with open("custom_cloud_init.sh", 'r') as file:
    userdata = file.readlines()

try:
    security_group_id = createSecurityGroup('others', [22, 5000])
except:
    pass

database_ip, instance_database = startAndGetIp("".join(userdata), 'database', 'others')


createCloudInitWithOpenVpn(customCommands = ["wget -O - https://raw.githubusercontent.com/brunoartc/cloud_serverless/master/ec2.sh | bash"], openvpnFile="openvpn_clients/serverless.ovpn")

with open("custom_cloud_init.sh", 'r') as file:
    userdata = file.readlines()

serverless_ip, instance_serverless = startAndGetIp("".join(userdata), 'serverless', 'others')

checkState(instance_database)
checkState(instance_serverless)


try:
    security_group_id = createSecurityGroup('autoscaling', [80, 22, 5000])
except:
    pass

try:
    security_group_id = getSecurityGroupId()['SecurityGroups'][0]['GroupId']
except:
    pass

loadbalancername, loadbalancerinfo = createLoadBalancer([security_group_id])



autoscale = createAutoScale(instance_serverless)

print("\n\n\n\n\n-------  INFO SUMMARY -------\n\n")
print("-------  INSTANCES    -------\n")
print("TYPE=\tDATABASE\tIP=" + database_ip + "\t\tID="+instance_database)
print("TYPE=\tSERVERLESS\ttIP=" + serverless_ip + "\t\tID="+instance_serverless)
print("TYPE=\tVPN\t\tIP=" + openvpn_ip + "\t\tID="+instance_openvpn)
print("TYPE=\tLOADBALANCER\tDNS=\t", loadbalancerinfo['DNSName'])







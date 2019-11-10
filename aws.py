import boto3
import json
import time
import requests
from paramiko import SSHClient, SFTPClient
import paramiko

VL = 5

global ec2
ec2 = boto3.resource('ec2')

def createKey():
    global ec2
    

    key_pair = ec2.create_key_pair(KeyName='toranja-script')

    KeyPairOut = str(key_pair.key_material)

    with open('key.pem','w') as file:
        file.write(KeyPairOut)


def createInstance(userdata = None, type = 'default'):

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



def startAndGetIp(cloud_init, tag):
    if (VL > 0):
        print("Start.    launching instance ... " + tag)
    instances = createInstance(cloud_init, tag)
    response = ec2.Instance(instances[0][1])
    while (response.public_ip_address == None):
        response = ec2.Instance(instances[0][1])
    if (VL > 2):
        print("Info.     Instance ip : " + response.public_ip_address)
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
        print("Check.    checking server on ... " + ip, end="")
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
    print("Done.     server up on " + ip)
    return 
    

def SFTP_script(ip, dire, origi, dest):
    
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
    t = client.get_transport()
    sftp = SFTPClient.from_transport(t)
    
    if (dire == 1):
        if (VL > 4):
            print("Get.  Getting files(" + origi + ") from " + ip)
        for i in range(len(dest)):
            sftp.get(origi[i], dest[i])
    else:
        if (VL > 4):
            print("Send.     Sending files(" + origi + ") to " + ip)
        for i in range(len(dest)):
            sftp.put(origi[i], dest[i])

def startVpnSerrion(ip, file):
    for i in range(len(ip)):
        if (VL > 3):
            print("Start.    Starting VPN session on " + ip[i])
        SFTP_script(ip[i], 0, [file[i]], ['/home/ubuntu/openvpn_client.conf'])
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip[i], port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
        client.exec_command("sudo tmux new -d -s vpn 'openvpn --config /home/ubuntu/openvpn_client.conf;'" )
        if (VL > 3):
            print("Done.     VPN session started on " + ip[i])



#createKey()


openvpn_ip, instance_openvpn = startAndGetIp('''#!/bin/bash
    wget -O - https://raw.githubusercontent.com/brunoartc/openvpn-init-script/master/openvpn.sh | bash''', 'vpn')


serverless_ip, instance_serverless = startAndGetIp('''#!/bin/bash
wget -O - https://raw.githubusercontent.com/brunoartc/cloud_serverless/master/ec2.sh | bash''', 'serverless')

database_ip, instance_database = startAndGetIp('''#!/bin/bash
wget -O - https://raw.githubusercontent.com/brunoartc/cloud_database/master/ec2.sh | bash''', 'database')

checkServer(openvpn_ip)

checkState(instance_database)
checkState(instance_serverless)


SFTP_script(openvpn_ip, 1, ["/home/ubuntu/openvpn/clients/database.ovpn", "/home/ubuntu/openvpn/clients/serverless.ovpn"], ["./openvpn_clients/database.ovpn", "./openvpn_clients/serverless.ovpn"])


startVpnSerrion([database_ip, serverless_ip], ["./openvpn_clients/database.ovpn", "./openvpn_clients/serverless.ovpn"])








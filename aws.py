import boto3
import json
import time
import requests
from paramiko import SSHClient, SFTPClient
import paramiko

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
    print("Started" + tag)
    instances = createInstance(cloud_init, tag)
    response = ec2.Instance(instances[0][1])
    while (response.public_ip_address == None):
        response = ec2.Instance(instances[0][1])
    print("OpenVpn = " + response.public_ip_address)
    ip = response.public_ip_address
    return ip

def checkServer(ip):
    print("OpenVPN configuration check started on " + ip)
    try:
        r = requests.get(url = "http://" + ip)
    except:
        r = None
    while (r==None or r.status_code != 200):
        print(".", end="")
        try:
            r = requests.get(url = "http://" + ip)
        except:
            r = None
        time.sleep(5)
        
    print("Done")
    return 
    

def SFTP_script(ip, dire, origi, dest):
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
    t = client.get_transport()
    sftp = SFTPClient.from_transport(t)
    if (dire == 1):
        for i in range(len(dest)):
            sftp.get(origi[i], dest[i])
    else:
        for i in range(len(dest)):
            sftp.put(origi[i], dest[i])

def startVpnSerrion(ip, file):
    for i in range(len(ip)):
        SFTP_script(ip[i], 0, file[i], '/home/ubuntu/openvpn_client.conf')
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=22, username='ubuntu', password=None, pkey=None, key_filename='key.pem', look_for_keys=True)
        client.exec_command("sudo tmux new -d -s todo 'openvpn --config /home/ubuntu/openvpn_client.conf;'" )



#createKey()


openvpn_ip = startAndGetIp('''#!/bin/bash
    wget -O - https://raw.githubusercontent.com/brunoartc/openvpn-init-script/master/openvpn.sh | bash''', 'vpn')


serverless_ip = startAndGetIp('''#!/bin/bash
wget -O - https://raw.githubusercontent.com/brunoartc/cloud_serverless/master/ec2.sh | bash''', 'serverless')

database_ip = startAndGetIp('''#!/bin/bash
wget -O - https://raw.githubusercontent.com/brunoartc/cloud_database/master/ec2.sh | bash''', 'database')

checkServer(openvpn_ip)




SFTP_script(openvpn_ip, 1, ["/home/ubuntu/openvpn/clients/database.ovpn", "/home/ubuntu/openvpn/clients/serverless.ovpn"], ["./openvpn_clients/database.ovpn", "./openvpn_clients/serverless.ovpn"])
time.sleep(30) #TODO: check health status AWS instead


startVpnSerrion([database_ip, serverless_ip], ["/home/ubuntu/openvpn/clients/database.ovpn", "/home/ubuntu/openvpn/clients/serverless.ovpn"])








from __future__ import print_function
import boto3
import os
import subprocess
import paramiko
import cryptography
import time
import logging
import paramiko

logging.getLogger("paramiko").setLevel(logging.DEBUG) 

#referencing this AWS blog post which recommends paramiko for SSH:
#https://aws.amazon.com/blogs/compute/scheduling-ssh-jobs-using-aws-lambda/

def configure_firebox(event, context):
    
    bucket=os.environ['Bucket']
    fireboxip=os.environ['FireboxIp']
    managementsubnetcidr=os.environ['ManagmenetCidr']
    webserversubnetcidr=os.environ['WebServerCidr']
    key="firebox-cli-ec2-key.pem"
    localkeyfile="/tmp/fb.pem"
    s3=boto3.client('s3')
    
    #####
    #save key to lambda to use for CLI connection
    #####
    print ('Get SSH key from S3 bucket')
    s3.download_file(bucket, key, localkeyfile)

    #####
    # Connect to Firebox via CLI
    ###
    k = paramiko.RSAKey.from_private_key_file(localkeyfile)
    c = paramiko.SSHClient()

    managementsubnetcidr=""

    try:

        #override check in known hosts file
        #https://github.com/paramiko/paramiko/issues/340
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print("connecting to " + fireboxip)
        c.connect( hostname = fireboxip, port = 4118, username = "admin", key_filename = localkeyfile)
        print("connected to " + fireboxip)

        channel = c.invoke_shell()

        command="configure\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        command="global-setting report-data enable\n"
        channel.send(command)
        time.sleep(3)
        
        output=channel.recv(2024)
        print(output)

        #make Firebox an NTP server
        #http://www.watchguard.com/help/docs/fireware/11/en-US/Content/en-US/basicadmin/NTP_server_enable_add_c.html
        command="ntp enable\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        command="ntp device-as-server enable\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        #need to figure out how to create a new policy-type
        #command="policy-type http protocol tcp 80\n"
        #channel.send(command)
        #time.sleep(3)
        #output=channel.recv(2024)
        #print(output)
        
        command="policy\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        command="rule http out\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        #allow all since AWS public NACL rules only allow out to S3 cidrs
        command="policy-type HTTP-proxy from alias Any-Trusted to alias Any-External\n"
        channel.sendall(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        command="rule 443-S3-out\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        #allow all since AWS public NACL rules only allow out to S3 cidrs
        command="policy-type HTTPS-proxy from alias Any-Trusted to alias Any-External\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)

        command="apply\n"
        channel.send(command)
        time.sleep(3)

        output=channel.recv(2024)
        print(output)
    
        #command="exit\n"
        #channel.send(command)
        #time.sleep(3)

        #output=channel.recv(2024)
        #print(output)

    finally:
        if channel:
            channel.close()
            print ("channel closed")
        if c:
            c.close()
            print ("connection closed")

    return 'success'

#if content returned is too long can use this    
def _wait_for_data(self, options, verbose=False):
    chan = self.chan
    data = ""
    while True:
        x = chan.recv(1024)
        if len(x) == 0:
            self.log("*** Connection terminated\r")
            sys.exit(3)
        data += x
        if verbose:
            sys.stdout.write(x)
            sys.stdout.flush()
        for i in range(len(options)):
            if re.search(options[i], data):
                return i
    return -1
    
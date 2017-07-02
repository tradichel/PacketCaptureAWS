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
    
    #get environment vars defined in lambda.yaml
    bucket=os.environ['Bucket']
    fireboxip=os.environ['FireboxIp']
    managementsubnetcidr=os.environ['ManagementCidr']
    webserversubnetcidr=os.environ['WebServerCidr']
    admincidr=os.environ['AdminCidr']
    sshkey=os.environ['Key']

    localkeyfile="/tmp/fb.pem"
    s3=boto3.client('s3')
    
    ###
    #turn on detailed request logging to troubleshoot
    #S3 endpoint connection errors
    ###
    #boto3.set_stream_logger(name='botocore')
    
    #####
    #save key to lambda to use for CLI connection
    #####
    print ("Get SSH key from S3 bucket")
    s3.download_file(bucket, sshkey, localkeyfile)

    #####
    # Set up SSH client
    ###
    k = paramiko.RSAKey.from_private_key_file(localkeyfile)
    c = paramiko.SSHClient()

    try:

        #override check in known hosts file
        #https://github.com/paramiko/paramiko/issues/340
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print("connecting to " + fireboxip)
        c.connect( hostname = fireboxip, port = 4118, username = "admin", key_filename = localkeyfile)
        print("connected to " + fireboxip)

        channel = c.invoke_shell()

        run_command(channel, "configure")
        run_command(channel, "global-setting report-data enable")
        run_command(channel, "ntp enable")
        run_command(channel, "ntp device-as-server enable")
        run_command(channel, "policy")
        add_cidr_rule(channel, "admin-ssh", admincidr, managementsubnetcidr, "tcp", "22")
        add_cidr_rule(channel, "admin-ssh", admincidr, webserversubnetcidr, "tcp", "22")
        add_alias_rule(channel, "HTTP-proxy", "Any-Trusted", "Any-External", "tcp", "80")
        add_alias_rule(channel, "HTTPS-proxy", "Any-Trusted", "Any-External", "tcp", "443")
    except ValueError as err:
        print(err.args)  
    finally:
        if channel:
            channel.close()
            print ("channel closed")
        if c:
            c.close()
            print ("connection closed")

    return 'success'

#good error handling info
#https://stackoverflow.com/questions/2052390/manually-raising-throwing-an-exception-in-python
def add_alias_rule(channel, aliasfrom, aliasto, policyname, protocol, port):
    try:
        run_command(channel, "rule https-out")
        run_command(channel, "policy-type " + policyname + " from alias " + aliasfrom + " to " + aliasto + " Any-External")
        run_command(channel, "apply")
        run_command(channel, "exit")
    except ValueError as err:
        raise

def add_cidr_rule(channel, cidrfrom, cidrto, policyname, protocol, port):
    try:
        run_command (channel, "policy-type " + policyname + " protocol " + protocol + " " + port)
        run_command(channel, "policy-type " + policyname + " from network-ip " + cidrfrom + " to newtork-ip " + cidrto + " firebox allowed")
        run_command(channel, "apply")
        run_command(channel, "exit")
    except ValueError as err:
        raise

def run_command(channel, command):
    c=command + "\n"
    channel.send(c)
    time.sleep(3)
    output=channel.recv(2024)
    print(output)
    #check for an error here and change the
    #return value on error
    if output.find('^')!=-1:
        raise ValueError('Error executing firebox command', command)
    

#if content returned is too long can use this    
def _wait_for_data(channel, options, verbose=False):
    chan = channel
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
    
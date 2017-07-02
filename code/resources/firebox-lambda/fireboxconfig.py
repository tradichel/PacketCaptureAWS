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

#good error handling info
#https://stackoverflow.com/questions/2052390/manually-raising-throwing-an-exception-in-python

def configure_firebox(event, context):
    
    #get environment vars defined in lambda.yaml
    #should validate these values ...
    bucket=os.environ['Bucket']
    fireboxip=os.environ['FireboxIp']
    managementsubnetcidr=os.environ['ManagementCidr']
    webserversubnetcidr=os.environ['WebServerCidr']
    admincidr=os.environ['AdminCidr']
    sshkey=os.environ['Key']

    localkeyfile="/tmp/fb.pem"
    s3=boto3.client('s3')
    
    #For troubleshooting AWS requests if needed
    #boto3.set_stream_logger(name='botocore')

    s3.download_file(bucket, sshkey, localkeyfile)

    channel, sshclient = connect(fireboxip, localkeyfile)
    
    try:
        #show some of the firebox configuration
        #run_command(channel, "show global-setting")
        run_command(channel, "show rule")

        #create required configuration
        run_command(channel, "configure")
        run_command(channel, "global-setting report-data enable")
        run_command(channel, "ntp enable")
        run_command(channel, "ntp device-as-server enable")
        add_rule(channel, "HTTP-Out", "HTTP-proxy", "Any-Trusted", "Any-External", "alias")
        add_rule(channel, "HTTPS-Out", "HTTPS-proxy", "Any-Trusted", "Any-External", "alias")
        add_policy_and_rule(channel, "admin-ssh-mgt", "admin-ssh", "tcp", "22", admincidr, managementsubnetcidr, "network-ip", "firewall allowed")
        add_policy_and_rule(channel, "admin-ssh-web", "admin-ssh", "tcp", "22", admincidr, webserversubnetcidr, "network-ip", "firewall allowed")
        
    #if an exception was raised, print before exit  
    except ValueError as err:
        print(err.args)  
        run_command(channel, "exit")

    #always close connections in a finally block
    finally:
        if channel:
            channel.close()
            print ("channel closed")
        if sshclient:
            sshclient.close()
            print ("connection closed")

    return 'success'

def connect(fireboxip, localkeyfile):
    
    k = paramiko.RSAKey.from_private_key_file(localkeyfile)
    c = paramiko.SSHClient()
    
    #override check in known hosts file
    #https://github.com/paramiko/paramiko/issues/340
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("connecting to " + fireboxip)
    c.connect( hostname = fireboxip, port = 4118, username = "admin", key_filename = localkeyfile)
    print("connected to " + fireboxip)

    channel = c.invoke_shell()

    return channel, c

def add_policy(channel, policyname, protocol, port):
    try:
        run_command (channel, "policy")
        run_command (channel, "policy-type " + policyname + " protocol " + protocol + " " + port)
        run_command (channel, "apply")
    except ValueError as err:
        raise
    finally:
        run_command (channel, "exit") #policy mode exit

def add_policy_and_rule(channel, rulename, policyname, protocol, port, addressfrom, addressto, type, options):
    try:
        add_policy(channel, policyname, protocol, port)
        add_rule(channel, rulename, policyname, addressfrom, addressto, options)
    except ValueError as err:
        raise

def add_rule(channel, rulename, policyname, addressfrom, addressto, options):
    try:
        run_command(channel, "rule " + rulename)
        run_command(channel, "policy-type " + policyname + " from alias " + aliasfrom + " to alias " + aliasto)
        run_command(channel, "apply")
    except ValueError as err:
        raise
    finally:
        run_command(channel, "exit") #rule mode exit

def run_command(channel, command):

    buff_size=2024
    c=command + "\n"
    channel.send(c)

    #wait for results to be buffered
    while not (channel.recv_ready()):
        if channel.exit_status_ready():
            print ("Channel exiting. No data returned")
            return
        time.sleep(3) 

    #print results 
    while channel.recv_ready():
        output=channel.recv(buff_size)
        print(output)
        
    #WatchGuard errors have ^ in output
    #throw an exception if we get a WatchGuard error
    if output.find('^')!=-1 or output.find('Error')!=-1:
        raise ValueError('Error executing firebox command', command)
    

        
    
from __future__ import print_function
import boto3
import os
import subprocess
import paramiko
import cryptography
import time
import logging
import paramiko

#cahnge to DEBUG for detailed error messages
logging.getLogger("paramiko").setLevel(logging.ERROR) 

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

        try:

            #main mode
            #run_command(channel, "show rule")
            #run_command(channel, "show policy-type")

            #configure mode
            run_command(channel, "configure")

            #global settings
            run_command(channel, "global-setting report-data enable")
            run_command(channel, "ntp enable")
            run_command(channel, "ntp device-as-server enable")

            #rules
            log=True

            add_rule(channel, "admin-ssh-management", "admin-ssh",  admincidr, managementsubnetcidr, "network-ip", log)
            add_rule(channel, "admin-ssh-web", "admin-ssh",  admincidr, webserversubnetcidr, "network-ip", log)
        
            add_rule(channel, "HTTPS-Out", "HTTPS-proxy", "Any-Trusted", "Any-External", "alias", log)
            add_rule(channel, "HTTP-Out", "HTTP-proxy", "tcp", "80", "Any-Trusted", "Any-External", "alias", log)

        except ValueError as err:
            raise
        finally:
            run_command(channel, "exit") #exit configure mode
            run_command(channel, "exit") #exit main mode

    #if an exception was raised, print before exit  
    except ValueError as err:
        print(err.args)  
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
        if str(err.args).find('already exists')!=-1:
            raise
        else:
            print(err.args) 
    finally:
        run_command (channel, "exit") #poliy

def add_policy_and_rule(channel, rulename, policyname, protocol, port, addressfrom, addressto, addrtype, options):
    try:
        add_policy(channel, policyname, protocol, port)
        add_rule(channel, rulename, policyname, addressfrom, addressto, addrtype, options)
    except ValueError as err:
        if str(err.args).find('already exists')!=-1:
            raise
        else:
            print(err.args) 

def add_rule(channel, rulename, policyname, addressfrom, addressto, addrtype, log):
    try:
        run_command (channel, "policy")
        run_command(channel, "rule " + rulename)
       
        rule = "policy-type " + policyname + " from " + addrtype + " " + addressfrom + " to " + addrtype + " " + addressto
        if addrtype=="alias":
            rule = rule + " firewall allowed"
        
        run_command(channel, rule)

        if log==True:
            run_command(channel, "logging log-message enable")

        run_command(channel, "apply")

    except ValueError as err:
        if str(err.args).find('already exists')!=-1:
            raise
        else:
            print(err.args) 
    finally:
        run_command (channel, "exit") #poliy

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
    
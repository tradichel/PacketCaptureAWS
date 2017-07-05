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

NOT_FOUND=-1
LOCAL_KEY_FILE="/tmp/fb.pem"

#policy names
POLICY_HTTP="HTTP-proxy" #port 80
POLICY_HTTPS="HTTPS-proxy" #port 443
POLICY_SSH="admin-ssh" #port 22

#rule names
RULE_SSH_MANAGE="admin-ssh-management"
RULE_SSH_WEB="admin-ssh-web"
RULE_HTTP_OUT="HTTP-Out"
RULE_HTTPS_OUT="HTTPS-Out"

LOG_TRAFFIC=True #log network rules
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
    s3=boto3.client('s3')
    
    #For troubleshooting AWS requests if needed
    #boto3.set_stream_logger(name='botocore')

    s3.download_file(bucket, sshkey, LOCAL_KEY_FILE)

    channel, sshclient = connect(fireboxip)
    
    try:

        #run_command(channel, "show policy-type")
        rule_ssh_manage_exists = check_rule_exists(channel, RULE_SSH_MANAGE)
        rule_ssh_web_exists = check_rule_exists(channel, RULE_SSH_WEB)
        rule_https_out_exists = check_rule_exists(channel, RULE_HTTPS_OUT)
        rule_http_out_exists = check_rule_exists(channel, RULE_HTTP_OUT)

        try:

            #configure mode
            run_command(channel, "configure")

            #global settings
            run_command(channel, "global-setting report-data enable")
            run_command(channel, "ntp enable")
            run_command(channel, "ntp device-as-server enable")

            #rules and policies
            if (rule_ssh_manage_exists == False):
                add_rule_and_policy(channel, POLICY_SSH, "tcp", "22", RULE_SSH_MANAGE,  admincidr, managementsubnetcidr, "network-ip", LOG_TRAFFIC)
            if (rule_ssh_web_exists == False):
                add_rule(channel, RULE_SSH_WEB, POLICY_SSH,  admincidr, webserversubnetcidr, "network-ip", LOG_TRAFFIC)
            if (rule_https_out_exists == False):
                add_rule(channel, RULE_HTTPS_OUT, POLICY_HTTPS, "Any-Trusted", "Any-External", "alias", LOG_TRAFFIC)
            if (rule_http_out_exists == False):
                add_rule(channel, RULE_HTTP_OUT, POLICY_HTTP, "Any-Trusted", "Any-External", "alias", LOG_TRAFFIC)

        except ValueError as err:
            raise
        finally:
            print ("exit configure mode")
            run_command(channel, "exit") #exit configure mode
            print ("exit main mode")
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

def connect(fireboxip):
    
    k = paramiko.RSAKey.from_private_key_file(LOCAL_KEY_FILE)
    c = paramiko.SSHClient()
    
    #override check in known hosts file
    #https://github.com/paramiko/paramiko/issues/340
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("connecting to " + fireboxip)
    c.connect( hostname = fireboxip, port = 4118, username = "admin", key_filename = LOCAL_KEY_FILE)
    print("connected to " + fireboxip)

    channel = c.invoke_shell()

    return channel, c

def check_rule_exists(channel, rulename):
    output = run_command(channel, "show rule " + rulename, False)
    if(output.find("not found")==NOT_FOUND):
        print("Rule " + rulename + " exists.")
        return True
    else:
        print("Rule " + rulename + " does not exist.")
        return False

def add_rule_and_policy(channel, policyname, protocol, port, rulename, addressfrom, addressto, addrtype, log):
    try:
        add_policy(channel, policyname, protocol, port)
        add_rule(channel, rulename, policyname, addressfrom, addressto, addrtype, log)
    except ValueError as err:
        raise

def add_policy(channel, policyname, protocol, port):
    try:
        run_command (channel, "policy")
        output = run_command (channel, "policy-type " + policyname + " protocol " + protocol + " " + port)
        if output.find('already exists')!=-NOT_FOUND:
            print("rule already exits")
        else:
            run_command (channel, "apply")

    except ValueError as err:
        if str(err.args).find('already exists')!=NOT_FOUND:
            raise
        else:
            print(err.args) 
    finally:
        print ("exit policy mode")
        run_command (channel, "exit") #policy

def add_rule(channel, rulename, policyname, addressfrom, addressto, addrtype, log):
    try:
        run_command (channel, "policy")
        run_command(channel, "rule " + rulename)
       
        rule = "policy-type " + policyname + " from " + addrtype + " " + addressfrom + " to " + addrtype + " " + addressto
        if addrtype=="alias":
            rule = rule + " firewall allowed"
        
        run_command(channel, rule)

        #do we have to run this twice??
        run_command(channel, "apply")

        if log==True:
            run_command(channel, "logging log-message enable")

        run_command(channel, "apply")

    except ValueError as err:
        if str(err.args).find('already exists')!=NOT_FOUND:
            raise
        else:
            print(err.args) 
    finally:
        print ("exit policy mode")
        run_command (channel, "exit") #policy

def run_command(channel, command, printoutput=True):

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
        if printoutput==True:
            print(output)
        
    #WatchGuard errors have ^ in output
    #throw an exception if we get a WatchGuard error
    if output.find('^')!=NOT_FOUND or output.find('Error')!=NOT_FOUND:
        raise ValueError('Error executing firebox command', command)

    return output
    
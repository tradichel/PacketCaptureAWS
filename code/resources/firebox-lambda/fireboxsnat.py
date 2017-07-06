from __future__ import print_function
import boto3
import os
import subprocess
import paramiko
import cryptography
import time
import logging
import paramiko

#implementing this, basically
#https://www.watchguard.com/help/configuration-examples/snat_web_server_configuration_example_(en-US).pdf

#cahnge to DEBUG for detailed error messages
logging.getLogger("paramiko").setLevel(logging.ERROR) 

NOT_FOUND=-1
LOCAL_KEY_FILE="/tmp/fb.pem"

#add a rule taht allows only the admin ip to access
#port 22 to get to the packet capture instance
POLICY_SSH="admin-ssh" #port 22
RULE_SSH_MANAGE="admin-ssh-management"
RULE_SSH_WEB="admin-ssh-web"

#port 80 to web site
POLICY_HTTP="HTTP-proxy" #port 80
RULE_HTTP_IN="http-in"

#snats
SNAT_WEB="web-srv-snat"
SNAT_PKT="packet-cap-svr-snat"

LOG_TRAFFIC=True #log network rules

def ConfigureSnat(event, context):

    #get environment vars defined in lambda.yaml
    #should validate these values ...
    bucket=os.environ['Bucket']
    webpublicip=['PublicIpWebServer']
    pktpublicip=['PublicIpPacketCapture']
    webip=os.environ['WebServerIP']
    pktip=os.environ['PacketCaptureServerIP']
    admincidr=os.environ['AdminCidr']
    sshkey=os.environ['Key']
    s3=boto3.client('s3')
    
    #For troubleshooting AWS requests if needed
    #boto3.set_stream_logger(name='botocore')
    s3.download_file(bucket, sshkey, LOCAL_KEY_FILE)

    channel, sshclient = connect(fireboxip)
    
    try:

        #check snat exists
        rule_http_in_exists = check_rule_exists(channel, RULE_HTTP_IN)
        rule_ssh_manage_exists = check_rule_exists(channel, RULE_SSH_MANAGE)
        rule_ssh_web_exists = check_rule_exists(channel, RULE_SSH_WEB)
        snat_web_exists = check_snat_exists(channel, SNAT_WEB)
        snat_exists_pkt_exists = check_snat_exists(channel, SNAT_PKT)
        
        try:

            #configure mode
            run_command(channel, "configure")

            if (snat_web_exists=False):
                add_snat(SNAT_WEB, webpublicip webip, 80)
            if (snat_pkt_exists=False):
                add_snat(SNAT_PKT, pktpublicip, pktip, 22)
            if (rule_ssh_manage_exists == False):
                add_rule_and_policy(channel, POLICY_SSH, "tcp", "22", RULE_SSH_MANAGE,  admincidr, SNAT_PKT, "snat", LOG_TRAFFIC)
            if (rule_http_in_exists == False):
                add_rule(channel, RULE_HTTP_IN, POLICY_HTTP,  admincidr, SNAT_WEB, "snat", LOG_TRAFFIC)
                        
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

def check_snat_exists(channel, snat)
    
    exist=False

    try:
        output = run_command(channel, "show snat " + snat, False)
        if(output.find("not found")==NOT_FOUND):
            print("SNAT " + rulename + " exists.")
            exist=True
    except ValueError as err:
        print(err.args)  
    
    return exist

#run from configuration mode
def add_snat(snatname, extip, intip, port)
    command="snat static-nat " + snatname + " external-ip " + extip intip + " port " + port
    run_command(channel, command)
except ValueError as err:
    if str(err.args).find('already exists')!=NOT_FOUND:
        raise
    else:
        print(err.args) 

    
#########################################################
#duplicated code could be pulled into a common library...
#########################################################

#This code assumes simply the rule exists not that it has the desired state
#If trying to verify or change a rule this code would need to be enhanced
def check_rule_exists(channel, rulename):
    
    exist=False

    try:
        output = run_command(channel, "show rule " + rulename, False)
        if(output.find("not found")==NOT_FOUND):
            print("Rule " + rulename + " exists.")
            exist=True
    except ValueError as err:
        print(err.args)  
    
    return exist

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
    
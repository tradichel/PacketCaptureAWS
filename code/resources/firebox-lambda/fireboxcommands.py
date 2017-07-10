import boto3
import paramiko
import time
import logging

##NOTE: If you are logged into the Firebox while trying to run 
##this Lambda function it will fail because only one admin can 
##edit at one time. Any issues with this DM me on Twitter.

#referencing this AWS blog post which recommends paramiko for SSH:
#https://aws.amazon.com/blogs/compute/scheduling-ssh-jobs-using-aws-lambda/

#good error handling info
#https://stackoverflow.com/questions/2052390/manually-raising-throwing-an-exception-in-python

class fireboxcommands:

    #local channel used to run commands
    channel=None
    sshclient=None
    
    #logging.getLogger("paramiko").setLevel(logging.DEBUG) 

    def __init__(self, bucket, sshkey, fireboxip):
        
        clone = self

        local_key_file="/tmp/fb.pem"

        #For troubleshooting AWS requests if needed
        #boto3.set_stream_logger(name='botocore')
        s3=boto3.client('s3')

        try:
            s3.download_file(bucket, sshkey, local_key_file)
        except:
            print ("cannot connect to S3 Bucket")
            raise #last time this failed was DNS error

        print ("try to connect to Firebox")
        try:
          
            k = paramiko.RSAKey.from_private_key_file(sshkey)
            clone.sshclient = paramiko.SSHClient()
            #override check in known hosts file
            #https://github.com/paramiko/paramiko/issues/340
            clone.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            clone.sshclient.connect( hostname = fireboxip, port = 4118, username = "admin", key_filename = local_key_file)
            clone.channel = clone.sshclient.invoke_shell()
        except:
            print ("cannot connect to firebox")
            raise

        print("connected to " + fireboxip)
        
        return clone

    #run from main mode
    def check_exists( object, name ):
        exist=False

        try:
            output = run_command( "show " + object + name, False)
            if(output.find("not found")==NOT_FOUND):
                print(object + " " + name + " exists.")
                exist=True
        except ValueError as err:
            print(err.args)  
        
        return exist      

    #run from configuration mode
    def add_snat(snatname, extip, intip, port):
        try:
            command="snat static-nat " + snatname + " external-ip " + extip + " " + intip + " port " + port
            run_command(command)
        except ValueError as err:
            if str(err.args).find('already exists')!=NOT_FOUND:
                raise
            else:
                print(err.args)   
    
    #run from main mode (?)
    def add_alias(name, description, aliastype, address):
        try:
            command="alias " + name + " description " + description + " " + aliastype + " " + address
        except ValueError as err:
            raise

    #run from policy mode
    def add_rule_and_policy(policyname, protocol, port, rulename, addressfrom, addressto, addrtype, log):
        try:
            add_policy(policyname, protocol, port)
            add_rule(rulename, policyname, addressfrom, addressto, addrtype, log)
        except ValueError as err:
            raise

    #run from policy mode
    def add_policy(policyname, protocol, port):
        try:
            run_command ("policy")
            output = run_command ("policy-type " + policyname + " protocol " + protocol + " " + port)
            if output.find('already exists')!=-NOT_FOUND:
                print("rule already exits")
            else:
                run_command ("apply")

        except ValueError as err:
            if str(err.args).find('already exists')!=NOT_FOUND:
                raise
            else:
                print(err.args) 
        finally:
            print ("exit policy mode")
            run_command ("exit") #policy

    #run from policy mode
    def add_rule(rulename, policyname, addressfrom, addressto, addrtype, log, ruleexists):
        try:

            #remove existing rule and re-add it
            if ruleexists==True:
                run_command("no rule " + rulename)
            run_command ("policy")
            run_command("rule " + rulename)
           
            rule = "policy-type " + policyname + " from " + addrtype + " " + addressfrom + " to " + addrtype + " " + addressto
            if addrtype=="alias":
                rule = rule + " firewall allowed"
            run_command(rule)

            if log==True:
                run_command("logging log-message enable")

            run_command("apply")

        except ValueError as err:
            if str(err.args).find('already exists')!=NOT_FOUND:
                raise
            else:
                print(err.args) 
        finally:
            print ("exit policy mode")
            run_command ("exit") #policy

    #run command
    def exe(command, printoutput=True):

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

    def exit():
        run_command("exit")

    #always close connections in a finally block
    def close_connections():
        if channel:
            channel.close()
            print ("channel closed")
        
        if sshclient:
            sshclient.close()
            print ("connection closed")
import boto3
import paramiko
import time
import logging
from botocore.client import Config

NOT_FOUND=-1

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
    
    logging.getLogger("paramiko").setLevel(logging.DEBUG) 

    def __init__(self, bucket, sshkey, fireboxip):

        clone=self

        local_key_file="/tmp/fb.pem"

        #For troubleshooting AWS requests if needed
        boto3.set_stream_logger(name='botocore')
        config = Config(connect_timeout=200, read_timeout=200, s3={'addressing_style': 'virtual'})
        s3=boto3.client('s3', config=config)

        try:
            s3.download_file(bucket, sshkey, local_key_file)
        except:
            print ("cannot connect to S3 Bucket")
            raise #last time this failed was DNS error

        print ("try to connect to Firebox")
        try:
          
            k = paramiko.RSAKey.from_private_key_file(local_key_file)
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

    #run from main mode
    def check_exists(self, object, name ):

        exist=False

        try:
            output = self.exe("show " + object + " " + name, False)
            if(output.find("name")!=NOT_FOUND or output.find("escription")!=NOT_FOUND):
                exist=True
        except ValueError as err:
            output = ''.join(err.args)
            if (output.find("not found")==NOT_FOUND and output.find("Fail to find")==NOT_FOUND):
                #error is something other than not found
                raise

        if (exist==True):
            print(object + " " + name + " exists.")
        else:
            print(object + " " + name + " does not exist.")
            #print(output)

        return exist      

    #run from configuration mode
    def add_snat(self, snatname, addrtype, extip, intip, port, snatexists):
        try:
            if (snatexists==True):
                #this fails with snat in use
                #self.delete("snat", snatname)
                return
            command="snat " + snatname + " static-nat " + addrtype + " " + extip + " " + intip + " port " + port
            self.exe(command)
        except ValueError as err:
            if str(err.args).find('already exists')!=NOT_FOUND:
                raise
            else:
                print(err.args)   
    
    #run from policy mode
    def add_alias(self, name, description, aliastype, address, aliasexists):
        try:
            if aliasexists == True:
                self.delete("alias", name)
            if aliastype=="FQDN":
                command="alias " + name + " " + aliastype + " \"" + address + "\""        
            else:
                command="alias " + name + " " + aliastype + " " + address   
            self.exe(command)
        except ValueError as err:
            print(err.args)
            print("For now if alias is in use leave it...talking to engineering about this")

    #run from policy mode
    def add_rule_and_policy(self, policyname, protocol, port, rulename, addressfrom, addressto, addrtypefrom, addrtypeto, log, ruleexists):
        try:
            if ruleexists == True:
                self.delete("rule", rulename)
            self.add_policy(policyname, protocol, port)
            self.add_rule(rulename, policyname, addressfrom, addressto, addrtypefrom, addrtypeto, log, ruleexists)
        except ValueError as err:
            raise

    #run from policy mode
    def add_policy(self, policyname, protocol, port):
        try:
            output = self.exe("policy-type " + policyname + " protocol " + protocol + " " + port)
            if output.find('already exists')!=-NOT_FOUND:
                print("policy already exits")
        except ValueError as err:
            if str(err.args).find('already exists')!=NOT_FOUND:
                raise
            else:
                print(err.args) 

    def delete(self, itemtype, name):
        self.exe("no " + itemtype + " " + name)

    #run from policy mode
    def add_rule(self, rulename, policyname, addressfrom, addressto, addrtypefrom, addrtypeto, log, ruleexists):
        #remove existing rule and re-add it
        if ruleexists==True:
            self.delete("rule", rulename)
        self.exe("rule " + rulename)
        try:   
            rule = "policy-type " + policyname + " from " + addrtypefrom + " " + addressfrom + " to " + addrtypeto + " " + addressto
            if addrtypefrom=="alias" or addrtypeto=="alias":
                rule = rule + " firewall allowed"
            self.exe(rule)
            if log==True:
                self.exe("logging log-message enable")
            self.apply() #if we got this far apply the changes
        except ValueError as err:
            if str(err.args).find('already exists')==NOT_FOUND:
                print ("Raise error")
            else:
                print(err.args) 
        finally:
            self.exit() #exit rule

    #run_command
    def exe(self, command, printoutput=True):

        buff_size=2024
        c=command + "\n"
        self.channel.send(c)

        #wait for results to be buffered
        while not (self.channel.recv_ready()):
            if self.channel.exit_status_ready():
                print ("Channel exiting. No data returned")
                return
            time.sleep(3) 

        #print results 
        while self.channel.recv_ready():
            output=self.channel.recv(buff_size)
            if printoutput==True:
                print(output)

        #WatchGuard errors have ^ in output
        #throw an exception if we get a WatchGuard error
        if output.find('^')!=NOT_FOUND or output.find('Error')!=NOT_FOUND:
            raise ValueError('Error executing firebox command: ' + output, command)

        return output

    #this assumes NTP is not already enabled nad rules have
    #not been set
    def enable_ntp(self):
        self.exe("ntp enable")
        self.exe("ntp device-as-server enable")
        #fix ntp rule to only allow NTP servers via DNS
        #these are not working currently...asking WG engineering team...
        self.policy()
        try:
            output = self.add_alias(ALIAS_NTP, "NTP Pool", "FQDN", "*.ntp.org", alias_ntp_exists)
            #rule to allow Firebox to rach out to NTP servers
            output = self.add_rule(RULE_NTP, POLICY_NTP, "Any-External", ALIAS_NTP, "alias", "alias", LOG_TRAFFIC, False)
            #cmd.add_rule(RULE_NTP, POLICY_NTP, "Any-Trusted", "Any-External", "alias", "alias", LOG_TRAFFIC, True)
            #cmd.add_rule(RULE_NTP, POLICY_NTP, "Any-Optional", "Any-External", "alias", "alias", LOG_TRAFFIC, False) #do not delete, update
        except:
            print("Error enabling NTP:")
            print(output)
        finally:
            self.exit() #exit policy
            
    def enable_threat_intel(self):
        self.exe("global-setting report-data enable")

    def configure(self):
        self.exe("configure")

    def policy(self):
        self.exe("policy")

    def apply(self):
        self.exe("apply")

    def exit(self):
        try:
            self.exe("exit")
        except:
            print("Maybe one too many exits?")  
            
    #always close connections in a finally block
    def close_connections(self):
        if self.channel:
            self.channel.close()
            print ("channel closed")
        
        if self.sshclient:
            self.sshclient.close()
            print ("connection closed")
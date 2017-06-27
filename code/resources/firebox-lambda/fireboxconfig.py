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
    webservercidr=os.environ['WebServerCidr']
    admincidr=os.environ['AdminCidr']
    key="firebox-cli-ec2-key.pem"
    localkeyfile="/tmp/fb.pem"
    s3=boto3.client('s3')
 
    #####
    #save key to lambda to use for CLI connection
    #####
    print ('Get SSH key from S3 bucket')

    #aws s3 cp resources/firebox-lambda/fireboxconfig.zip s3://$bucket/fireboxconfig.zip --sse AES256 > upload.txt  2>&1  
    #s3.download_file(bucket, key, localkeyfile, {'SSECustomerAlgorithm': 'AES256'})
    s3.download_file(bucket, key, localkeyfile)
    
    #if need to view key - note this displays key
    #in cloudwatch logs
    #f = open(localkeyfile, 'r')
    #print (f.read())
    #f.close()
    
    #####
    # Connect to Firebox via CLI
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

        try:
            
            channel = c.invoke_shell()
            command="configure\n"
            channel.send(command)
            time.sleep(3)
            
            #send feedback to WatchGUard for Security Report
            #https://www.watchguard.com/wgrd-resource-center/security-report
            command="global-setting report-data enable\n"
            channel.send(command)
            time.sleep(3)
            
            #make Firebox an NTP server
            #http://www.watchguard.com/help/docs/fireware/11/en-US/Content/en-US/basicadmin/NTP_server_enable_add_c.html
            command="ntp enable\n"
            channel.send(command)
            time.sleep(3)

            command="ntp device-as-server enable\n"
            channel.send(command)
            time.sleep(3)
      
            #switch to policy mode
            command="policy\n"
            channel.send(command)
            time.sleep(3)

            #outbound for S3
            #for x in range(0, 6):
            #    varname='s3cidr'+x
            #    print(varname)
            #    envar = s.environ[varname]
            #    if envar != "":
            #        print(envar)
                    #open traffic outbound on port 80 and 443
                    #to the IP in the environment variable
                    #command="policy\n"
                    #channel.send(command)
                    #time.sleep(3)
            
            command="help https-proxy\n"
            channel.send(command)
            time.sleep(3)

            #create a policy to allow
            #the admin user SSH to packet capture server
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            #ephemeral ports out from packet capture server to admin
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            #create a policy to allow
            #the admin user SSH to web server
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            #ephemeral ports out from web server to all
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            #allow traffic on port 80 to the web server
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            #remove any other ports
            #command="policy\n"
            #channel.send(command)
            #time.sleep(3)

            output=channel.recv(2024)
            print(output)

        finally:
            if channel:
                channel.close()
                print ("channel closed")
    finally:
        if c:
            c.close()
            print ("connection closed")

    return 'success'
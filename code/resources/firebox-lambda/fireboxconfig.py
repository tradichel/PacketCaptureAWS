from __future__ import print_function
import os
from fireboxcommands import fireboxcommands

NOT_FOUND=-1

POLICY_HTTP="HTTP-proxy" #port 80
POLICY_HTTPS="HTTPS-proxy" #port 443
RULE_HTTP_OUT="HTTP-Out"
RULE_HTTPS_OUT="HTTPS-Out"
ALIAS_NTP="NTP-Pool"

LOG_TRAFFIC=True #log network rules

def configure_firebox(event, context):

    #get environment vars defined in lambda.yaml
    #should validate these values ...
    bucket=os.environ['Bucket']
    sshkey=os.environ['Key']
    fireboxip=os.environ['FireboxIp']
    managementsubnetcidr=os.environ['ManagementCidr']
    webserversubnetcidr=os.environ['WebServerCidr']
    admincidr=os.environ['AdminCidr']
    
    cmd = fireboxcommands(bucket, sshkey, fireboxip)    
    
    try:

        rule_https_out_exists = cmd.check_exists("rule", RULE_HTTPS_OUT)
        rule_http_out_exists = cmd.check_exists("rule", RULE_HTTP_OUT)
        alias_ntp_exists = cmd.check_exists("alias", ALIAS_NTP)

        try:

            #configure mode
            cmd.exe("configure")

            #threat intel
            cmd.exe("global-setting report-data enable")
            
            #use firebox as ntp server
            cmd.exe("ntp enable")
            cmd.exe("ntp device-as-server enable")

            #alias for NTP FQDN
            cmd.add_alias(ALIAS_NTP, "NTP Pool", "FQDN", "*.ntp.org", alias_ntp_exists)

            #fix the NTP rule to only go to desired hosts. By default it goes anywhere in the Internet
            cmd.add_rule(RULE_NTP, POLICY_NTP, "Any-Trusted", ALIAS_NTP, "alias", LOG_TRAFFIC, True)
            cmd.add_rule(RULE_HTTPS_OUT, POLICY_HTTPS, "Any-Trusted", "Any-External", "alias", LOG_TRAFFIC, rule_https_out_exists)
            cmd.add_rule(RULE_HTTP_OUT, POLICY_HTTP, "Any-Trusted", "Any-External", "alias", LOG_TRAFFIC, rule_http_out_exists)
        
        except ValueError as err:
            raise
        finally:
            cmd.exit() #exit configure mode
            cmd.exit() #exit main mode

    #if an exception was raised, print before exit  
    except ValueError as err:
        print(err.args)  
    #always close connections in a finally block
    finally:
        cmd.close_connections()

    return 'success'
from __future__ import print_function
import os

NOT_FOUND=-1

POLICY_SSH="admin-ssh" #port 22
RULE_SSH_MANAGE="admin-ssh-management"
RULE_SSH_WEB="admin-ssh-web"

#port 80 to web site
POLICY_HTTP="HTTP-proxy"
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
    
    cmd = fireboxcommands(bucket, sshkey, fireboxip)   
    
    try:

        #check snat exists
        rule_http_in_exists = cmd.check_exists( "rule", RULE_HTTP_IN)
        rule_ssh_manage_exists = cmd.check_exists( "rule", RULE_SSH_MANAGE)
        rule_ssh_web_exists = cmd.check_exists( "rule", RULE_SSH_WEB)
        snat_web_exists = cmd.check_exists( "snat", SNAT_WEB)
        snat_exists_pkt_exists = cmd.check_exists( "snat", SNAT_PKT)

        try:

            #configure mode
            cmd.exe( "configure")

            add_snat(SNAT_WEB, webpublicip webip, "80", snat_web_exists)
            add_snat(SNAT_PKT, pktpublicip, pktip, "22", snat_pkt_exists)
            add_rule_and_policy( POLICY_SSH, "tcp", "22", RULE_SSH_MANAGE,  admincidr, SNAT_PKT, "snat", LOG_TRAFFIC, rule_ssh_manage_exists)
            add_rule( RULE_HTTP_IN, POLICY_HTTP,  admincidr, SNAT_WEB, "snat", LOG_TRAFFIC, rule_http_in_exists)
                        
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
        cmd.close()

    return 'success'

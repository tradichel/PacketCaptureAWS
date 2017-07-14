from __future__ import print_function
import os
from fireboxcommands import fireboxcommands

NOT_FOUND=-1

POLICY_SSH='SSH' #port 22
RULE_SSH_MANAGE='admin-ssh-management'
RULE_SSH_WEB='admin-ssh-web'

#port 80 to web site
POLICY_HTTP='HTTP-proxy'
RULE_HTTP_IN='http-in'

#snats
SNAT_WEB='web-srv-snat'

ALIAS_ADMIN_IP='admin-ip'

LOG_TRAFFIC=True #log network rules

def configure_snat(event, context):

    #get environment vars defined in lambda.yaml
    #should validate these values ...
    bucket=os.environ['Bucket']
    webip=os.environ['WebServerIP']
    sshkey=os.environ['Key']
    fireboxip=os.environ['FireboxIp']

    adminip = admincidr[:admincidr.find('/')] 

    cmd = fireboxcommands(bucket, sshkey, fireboxip)   
    
    try:

        #check snat exists
        rule_http_in_exists = cmd.check_exists( 'rule', RULE_HTTP_IN)
        rule_ssh_manage_exists = cmd.check_exists( 'rule', RULE_SSH_MANAGE)
        snat_web_exists = cmd.check_exists( 'snat', SNAT_WEB)

        try:

            #configure mode
            cmd.configure()
            cmd.policy()
            cmd.add_snat(SNAT_WEB, 'external-addr', 'Any-External', webip, '80', snat_web_exists)
            cmd.policy()
            cmd.add_rule( RULE_HTTP_IN, POLICY_HTTP,  'Any-External', SNAT_WEB, 'alias', 'snat', LOG_TRAFFIC, rule_http_in_exists)
                        
        except ValueError as err:
            raise
        finally:
            cmd.exit() #exit policy mode
            cmd.exit() #exit configure mode
            cmd.exit() #exit main mode

    #if an exception was raised, print before exit  
    except ValueError as err:
        print(err.args)  

    #always close connections in a finally block
    finally:
        cmd.close_connections()

    return 'success'
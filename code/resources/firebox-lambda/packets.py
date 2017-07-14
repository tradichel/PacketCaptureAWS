from __future__ import print_function
import os
from fireboxcommands import fireboxcommands

def capture_packets(event, context):

    #get environment vars defined in lambda.yaml
    #should validate these values ...
    bucket=os.environ['Bucket']
    sshkey=os.environ['Key']
    fireboxip=os.environ['FireboxIp']

    cmd = fireboxcommands(bucket, sshkey, fireboxip)    
    
    try:

        cmd.capture_packets()

    #if an exception was raised, print before exit  
    except ValueError as err:
        print(err.args)  
    #always close connections in a finally block
    finally:
        cmd.exit() #exit main mode
        cmd.close_connections()

    return 'success'
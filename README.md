Packet Capture on AWS

Questions? DM me @TeriRadichel on Twitter.

About This Repo:

    This repo creates the following AWS resources:
  
    - WatchGuard Firebox Cloud with three network interfaces
        - public Internet connected interface
        - private management interface
        - web server interface
    - An EC2 key to connect to the Firebox
    - S3 bucket and policy for key, lambda code
    - S3 bucket and policy for log files
    - A lambda function to configure the Firebox
    - KMS key for lambda function to encrypt variables
    - A packet capture instance that leverages the Firebox CLI
    - A Web Server to test packet capture
    - All the necessary networking and IAM resources

Before You Run This Script:

    Create an AWS account:
    https://aws.amazon.com (click the button to create an account)

    Enable MFA on your user ID that is used to run this script:
    http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html

    Install and configure the AWS CLI with your access key ID, secret key and region: 
    http://docs.aws.amazon.com/cli/latest/userguide/installing.html

    Install git:
    https://git-scm.com/

    Clone (download) this repo with this command: 
    git clone https://github.com/tradichel/PacketCaptureAWS.git

    If you are using Windows install a bash shell:
    https://www.howtogeek.com/249966/how-to-install-and-use-the-linux-bash-shell-on-windows-10/

    Install Python
    https://www.python.org

    Activate The Firebox AMI In Your Account:
    http://websitenotebook.blogspot.com/2017/05/manually-activating-watchguard-firebox.html


Run the code:

    Log into the console using MFA.

    Navigate to PacketCaptureAWS/code folder

    type ./run.sh

    At the prompt, type 1 and hit enter:

        Please select action:
        1) Create/Update
        2) Delete
        3) Cancel
        #? 

    The code will tell you the region your CLI is configured to use:

        ***
        * Begin: Mon Jun 26 21:20:00 HST 2017
        * ---- NOTE --------------------------------------------
        * Your CLI is configured for region:  us-west-2
        * Resources will be created in this region.
        * Switch to this region in console when you login.
        * ------------------------------------------------------

    When it asks if you want to use the default options type y and hit enter:

       * Would you like to use all the default options? (Y)
    
    If you want to change defaults, hit enter above. Read prompts.

    Watch the screen for updates.

    Log into the console to see what was created.

    To delete all the resources run the script again and choose delete.

    Check the console to see everything was deleted.
    
    ----

    Additional Info

    AWS:
    https://aws.amazon.com/getting-started/

    AWS IAM Best Practices (like MFA)
    http://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

    Cloning repos:
    https://git-scm.com/docs/git-clone

    ---

Now Run The Code (in the code directory):

    ./run.sh 

Follow the prompts.

> Select which action you want to take - create, update or delete resources. 

    Please select:
    1) Create
    2) Update
    3) Delete
    4) Cancel
    #? 

> Enter the CIDR that is allowed to upload files to your private S3 bucket or hit enter. 

    Enter the IP range allowed to access Firebox S3 bucket (default is 0.0.0.0/0)

> Select an AMI. The script will execute a command to produce a list of available AMIs. For example, if I want the Firebox Pay-As-You-Go version 11.12.2 I would enter ami-a844d4c8 at the prompt and hit enter. (If you don't see any then you need to follow the steps above to activate the AMI from the marketplace.)

    Available AMIs:
    ami-3b4ddd5b 
    firebox-cloud-11_12_2-526900-byol
    ami-a844d4c8 
    firebox-cloud-11_12_2-526900-payasyougo
    WatchGuard Marketplace AMI from list above:

> Enter an MFA token. Your session lasts 12 hours once created.

    MFA token (return to use active session):
    
Watch as your resources get created...

[When script is complete: browse to web server and view pcap files in S3 bucket]

TODO:

    - eth2 + networking for web servers
    - set up web server + routes to access from Interent
    - set up EC2 instance for packet capture
    - create pcap files in an S3 bucket

Questions?

    @teriradichel

More about Firebox Cloud:

    Set Up Firebox Cloud:
    https://www.watchguard.com/help/docs/fireware/11/en-US/Content/en-US/firebox_cloud/fb_cloud_help_intro.html

    Latest Firebox Documentation:
    https://www.watchguard.com/wgrd-help/documentation/xtm
    
    Contact a WatchGuard reseller:
    http://www.watchguard.com/wgrd-resource-center/how-to-buy?utm_source=teriradichel&utm_medium=gh&utm_campaign=gh

    Some resellers sell on Amazon:
    https://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%3Daps&field-keywords=watchguard&utm_source=teriradichel&&utm_medium=gh&utm_campaign=gh

Other Cloud Resources:

    Cloud Security:
    https://www.secplicity.org/2017/04/08/cloud-security/?utm_source=teriradichel&utm_medium=Twitter&utm_campaign=gh

    How Can Automation Improve Security?
    https://www.secplicity.org/2017/04/21/how-can-automation-improve-security/?utm_source=teriradichel&utm_medium=gh&utm_campaign=gh

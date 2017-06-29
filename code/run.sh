#!/bin/sh
##############################################################
# 
# Packet Capture Test
#
# Follow instructions in readme: 
# https://github.com/tradichel/PacketCaptureAWS
#
###############################################################
function get_latest_linux_ami (){
    owner=amazon
    amidesc=$(aws ec2 describe-images --owners $owner --filters "Name=virtualization-type,Values=hvm,Name=root-device-type,Values=ebs,Name=description,Values=*Amazon Linux AMI 20*"| grep "Description" | sort -r | grep "x86_64 HVM EBS" | grep -m1 -v "rc" | cut -d ":" -f 2 | sed -e 's/^[[:space:]]*//')
    echo $(get_image "$amidesc" $owner)
}

function get_default_admin_cidr(){
    yourip=$(curl -s https://whatismyip.akamai.com/)
    if [ "$yourip" == "" ]; then yourip=$(curl -s https://ifconfig.co/ip); fi
    if [ "yourip" != "" ]; then defaultadmincidr="$yourip/32";fi
    echo "$defaultadmincidr"
}

function get_latest_firebox_ami (){
    owner=679593333241
    #use the commented out line instead to verify the owner - takes a long time to run
    #amidesc=$(aws ec2 describe-images --owners $owner --filters "Name=description,Values=firebox*" | grep "Description" | grep "pay" | sort -r | grep -m1 -v "rc" | cut -d ":" -f 2 | sed -e 's/^[[:space:]]*//')
    amidesc=$(aws ec2 describe-images --filters "Name=description,Values=firebox*" | grep "Description" | grep "pay" | sort -r | grep -m1 -v "rc" | cut -d ":" -f 2 | sed -e 's/^[[:space:]]*//')
    echo $(get_image "$amidesc" $owner)
}

function get_image(){
    amidesc="$1"; owner="$2"
    #use the commented out line instead to verify the owner - takes a long time to run
    #imageid=$(aws ec2 describe-images --owners $owner --filters "Name=description,Values=$amidesc" | grep ImageId | cut -d ":" -f 2 | sed -e 's/^[[:space:]]*//' -e 's/,//') 
    imageid=$(aws ec2 describe-images --filters "Name=description,Values=$amidesc" | grep ImageId | cut -d ":" -f 2 | sed -e 's/^[[:space:]]*//' -e 's/,//') 
    echo $imageid
}

dt=$(date)
region=$(aws configure get region)
rm -f *.txt
echo "* ---- START FIREBOX SCRIPT ----------------------------"
echo "* $dt" 
echo "* ---- REGION ------------------------------------------"
echo "* Your CLI is configured for region: " $region
echo "* Resources will be created in this region."
echo "* Switch to this region in console when you login."
echo "* ------------------------------------------------------"

echo "Select action:"
select cudl in "Create/Update" "Delete" "Cancel"; do
    case $cudl in
        Create/Update ) action="create";break;;
        Delete ) action="delete";break;;
        Cancel ) exit;;
    esac
done

if [ "$action" != "delete" ]; then

    defaultinstancetype="c4.large"
    defaultpublicidr="10.0.0.0/24"
    defaultmanagementcidr="10.0.1.0/24"
    defaultwebcidr="10.0.2.0/24"
    defaultadmincidr=$(get_default_admin_cidr)

    echo "* ------------------------------------------------------"
    echo "Retrieving Firebox Cloud AMIs..."
    fireboxami=$(get_latest_firebox_ami)
    if [ "$fireboxami" = "" ]; then 
        echo "No Firebox AMIs have been activated in your account. Please see README.md"; 
        exit; 
    fi
    #display list of firebox amis 
    aws ec2 describe-images --filters "Name=description,Values=firebox*" | grep 'ImageId\|Description' | sed 'N;s/\n/ /'

    echo "Retrieving Amazon Linux AMI..."
    lami=$(get_latest_linux_ami)
    echo "* ------------------------------------------------------"

    echo "Default values:"
    echo "firebox ami: $fireboxami"
    echo "linux ami: $lami"
    echo "instance type: $defaultinstancetype"
    echo "public cidr: $defaultpubliccidr"
    echo "web cidr: $defaultwebcidr"
    echo "management cidr: $defaultmanagementcidr"

    if [ "$defaultadmincidr" == "" ]; then
        echo "Error retrieving your IP address from whatismyip.akami.com or https://ifconfig.co/ip. /
        You can manually visit this site to get your IP if needed: https://www.whatismyip.com: /
        You will need to enter your IP /32 e.g. x.x.x.x/32 or desired CIDR block"
    else
        echo "admin cidr: $defaultadmincidr"
    fi

    echo "* ------------------------------------------------------"
    echo "* Would you like to use all the default options? (Y)"
    read usedefault
    if [ "$usedefault" == "y" ]; then usedefault="Y"; fi

    if [ "$usedefault" != "Y" ]; then

        echo "Enter Firebox AMI (default: $fireboxami)"
        read ami
   
        echo "Packet Capture AMI (default: $lami):"
        read linuxami

        echo "Instance Type (default: c4.large - See README.md for requirements):"
        read instancetype

        echo "Public Subnet Cidr (default is 10.0.0.0/24):"
        read publiccidr

        echo "Web Server Subnet Cidr (default is 10.0.2.0/24):"
        read webservercidr

        echo "Management Subnet Cidr (default is 10.0.1.0/24):"
        read managementcidr
    
    fi
fi

if [ "$defaultadmincidr" = "" ]; then
    echo "Enter the Admin IP range (default: $yourip/32)"
    read adminips
fi

if [ "$ami" = "" ]; then ami="$fireboxami"; fi
if [ "$linuxami" = "" ]; then linuxami="$lami"; fi
if [ "$instancetype" = "" ]; then instancetype="$defaultinstancetype"; fi
if [ "$publiccidr" = "" ]; then publiccidr="$defaultpublicidr"; fi
if [ "$webservercidr" = "" ]; then webservercidr="$defaultwebcidr"; fi
if [ "$managementcidr" = "" ]; then managementcidr="$defaultmanagementcidr"; fi
if [ "$adminips" = "" ]; then adminips="$defaultadmincidr"; fi

#if user has enters MFA token get a new session.
echo "MFA token (default use active session):"
read mfatoken

#get the user information to get an active session with MFA
aws sts  get-caller-identity > "user.txt" 2>&1
userarn=$(./execute/get_value.sh "user.txt" "Arn")
account=$(./execute/get_value.sh "user.txt" "Account")
user=$(cut -d "/" -f 2 <<< $userarn)
mfaarn="arn:aws:iam::$account:mfa/$user"

if [ "$mfatoken" != "" ]
    then

    if [ "$error" != "" ]; then 
        echo $error 
        exit; 
    fi
    echo "mfatoken is required"
    echo "* ---- What's the problem? ----"
    echo "* Enable MFA on your account and enter MFA token at prompt."
    echo "* For more information about MFA:"
    echo "* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html"
    echo "* https://aws.amazon.com/premiumsupport/knowledge-center/authenticate-mfa-cli/"
    echo "* -----------------------------"
    exit
fi

if [ "$action" = "" ]; then echo "action cannot be null"; exit; fi
if [ "$user" = "" ]; then echo "adminuser cannot be null"; exit; fi
if [ "$adminips" = "" ]; then echo "adminips cannot be null"; exit; fi
if [ "$userarn" = "" ]; then echo "userarn cannot be null"; exit; fi
if [ "$ami" = "" ]; then echo "ami cannot be null"; exit; fi
if [ "$instancetype" = "" ]; then echo "instancetype cannot be null"; exit; fi
if [ "$linuxami" = "" ]; then echo "linuxami cannot be null"; exit; fi
if [ "$publiccidr" = "" ]; then echo "publiccidr cannot be null"; exit; fi
if [ "$managementcidr" = "" ]; then echo "managementcidr cannot be null"; exit; fi
if [ "$webservercidr" = "" ]; then echo "webservercidr cannot be null"; exit; fi


#if no errors create the stack
echo "Executing: $action with $user as admin user with ips: $adminips ami: $ami instancetype: $instancetype $linuxami" 
echo "* ------------------------------------------------------"
echo "
. ./execute/action.sh $action $user $adminips $userarn $ami $instancetype $linuxami $publiccidr $managementcidr $webservercidr"
. ./execute/action.sh $action $user $adminips $userarn $ami $instancetype $linuxami $publiccidr $managementcidr $webservercidr

rm -f *.txt
dt=$(date)
echo "Done $dt"
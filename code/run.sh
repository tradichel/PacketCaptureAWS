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


echo "Please select action:"
select cudl in "Create/Update" "Delete" "Cancel"; do
    case $cudl in
        Create/Update ) action="create";break;;
        Delete ) action="delete";break;;
        Cancel ) exit;;
    esac
done

dt=$(date)
region=$(aws configure get region)
rm -f *.txt
echo "***"
echo "* Begin: $dt" 
echo "* ---- NOTE --------------------------------------------"
echo "* Your CLI is configured for region: " $region
echo "* Resources will be created in this region."
echo "* Switch to this region in console when you login."
echo "* ------------------------------------------------------"

echo "* Would you like to use all the default options? (Y)"
read usedefault
if [ "$usedefault" == "y" ]; then usedefault="Y"; fi

if [ "$action" != "delete" ]
then
    
    yourip=$(curl -s https://whatismyip.akamai.com/)

    if [ "$yourip" == "" ]; then 
        yourip=$(curl -s https://ifconfig.co/ip)
    fi

    if [ "$yourip" == "" ]; then
        echo "Error retrieving your IP address from whatismyip.akami.com or https://ifconfig.co/ip. /
         You can manually visit this site to get your IP if needed: https://www.whatismyip.com: /
         Enter your IP /32 e.g. x.x.x.x/32 or desired CIDR block"
    fi

    if [ "$usedefault" != "Y" ] || [ "$yourip" == "" ]; then
        echo "Enter the Admin IP range (default: $yourip/32)"
        read adminips
    fi

    if [ "$adminips" == "" ]; then 
        if [ "$yourip" == "" ]; then

            echo "Must enter Admin IP range allowed to administer Firebox"
            exit
        else
            adminips="$yourip/32"; 
        fi
    fi

    echo "* ------------------------------------------------------"
    echo "Retrieving list of Firebox Cloud AMIs..."
    fireboxami=$(get_latest_firebox_ami)
    if [ "$fireboxami" = "" ]; then echo "No Firebox AMIs have been activated in your account. Please see README.md"; exit; fi
    aws ec2 describe-images --filters "Name=description,Values=firebox*" | grep 'ImageId\|Description' | sed 'N;s/\n/ /'
    if [ "$usedefault" != "Y" ]; then
        echo "Enter Firebox AMI (default: $fireboxami)"
        read ami
    fi
    if [ "$ami" = "" ]; then ami="$fireboxami"; fi
    
    echo "* ------------------------------------------------------"
    echo "Retrieving the latest Amazon Linux AMI..."
    lami=$(get_latest_linux_ami)
    if [ "$usedefault" != "Y" ]; then
        echo "Packet Capture AMI (default: $lami):"
        read linuxami
    fi
    if [ "$linuxami" = "" ]; then linuxami="$lami"; fi

    if [ "$usedefault" != "Y" ]; then
        echo "Instance Type (default: c4.large - See README.md for requirements):"
        read instancetype
    fi
    if [ "$instancetype" = "" ]; then instancetype="c4.large"; fi

fi

#get the user information to get an active session with MFA
aws sts  get-caller-identity > "user.txt" 2>&1
userarn=$(./execute/get_value.sh "user.txt" "Arn")
account=$(./execute/get_value.sh "user.txt" "Account")
user=$(cut -d "/" -f 2 <<< $userarn)

#if user has enters MFA token get a new session.
if [ "$usedefault" != "Y" ]; then
    echo "MFA token (default: active session, if exists):"
    read mfatoken
fi

if [ "$mfatoken" != "" ]
then
    mfaarn="arn:aws:iam::$account:mfa/$user"
    error=$(./execute/get_credentials.sh $mfaarn $mfatoken | grep "error\|Invalid") 
    if [ "$error" != "" ]; then 
        echo "* ---- What's the problem? ----"
        echo "* Enable MFA on your account and enter MFA token at prompt."
        echo "* For more information about MFA:"
        echo "* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html"
        echo "* https://aws.amazon.com/premiumsupport/knowledge-center/authenticate-mfa-cli/"
        echo "* -----------------------------"
        echo $error 
        exit; 
    fi
fi

#if no errors create the stack
echo "Executing: $action with $user as admin user with ips: $adminips ami: $ami instancetype: $instancetype $linuxami" 
echo "* ------------------------------------------------------"
. ./execute/action.sh $action $user $adminips $userarn $ami $instancetype $linuxami

rm -f *.txt
#dt=$(date)
echo "Done"
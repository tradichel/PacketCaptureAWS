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
select cudl in "Create" "Update" "Delete" "Cancel"; do
    case $cudl in
        Create ) action="create";break;;
        Update ) action="update";break;;
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

if [ "$action" != "delete" ]
then
    #todo: add this back to bucket policy
    yourip=$(curl -s http://whatismyip.akamai.com/)
    echo "Enter the Admin IP range (default: $yourip/32 < Your IP based on a query to http://whatismyip.akamai.com/)"
    read adminips
    if [ "$adminips" = "" ]; then adminips="$yourip/32"; fi

    echo "* ------------------------------------------------------"
    echo "Retrieving list of Firebox Cloud AMIs..."
    fireboxami=$(get_latest_firebox_ami)
    if [ "$fireboxami" = "" ]; then echo "No Firebox AMIs have been activated in your account. Please see README.md"; exit; fi
    aws ec2 describe-images --filters "Name=description,Values=firebox*" | grep 'ImageId\|Description' | sed 'N;s/\n/ /'
    echo "* ------------------------------------------------------"
    echo "Enter Firebox AMI (default: $fireboxami)"
    read ami
    if [ "$ami" = "" ]; then ami="$fireboxami"; fi
    
    echo "* ------------------------------------------------------"
    echo "Retrieving the latest Amazon Linux AMI..."
    lami=$(get_latest_linux_ami)
    echo "* ------------------------------------------------------"
    echo "Packet Capture AMI (default: $lami):"
    read linuxami
    if [ "$linuxami" = "" ]; then linuxami="$lami"; fi

    echo "Instance Type (default: c4.large - See README.md for requirements):"
    read instancetype
    if [ "$instancetype" = "" ]; then instancetype="c4.large"; fi

fi

#get the user information to get an active session with MFA
aws sts  get-caller-identity > "user.txt" 2>&1
userarn=$(./execute/get_value.sh "user.txt" "Arn")
account=$(./execute/get_value.sh "user.txt" "Account")
user=$(cut -d "/" -f 2 <<< $userarn)

#if user has enters MFA token get a new session.
echo "MFA token (default: active session, if exists):"
read mfatoken
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
. ./execute/action.sh $action $user $adminips $userarn $ami $instancetype $linuxami

rm -f *.txt
#dt=$(date)
echo "Done"
#!/bin/sh
mfa=$1;tokencode=$2

#get an STS session using MFA for bucket policy that requires MFA to upload files
aws sts get-session-token --serial-number $mfa --token-code $tokencode > "session.txt" 2>&1 
error=$(cat session.txt | grep "error\|Invalid")

if [ "$error" != "" ]
then 
    echo $error 
    exit
fi

accesskey=$(./execute/get_value.sh "session.txt" "AccessKeyId")
secretkey=$(./execute/get_value.sh "session.txt" "SecretAccessKey")
sessiontoken=$(./execute/get_value.sh "session.txt" "SessionToken")

#Linux/Mac
export AWS_ACCESS_KEY=$accesskey
export AWS_SECRET_ACCESS_KEY=$secretkey
export AWS_SESSION_TOKEN=$sessiontoken

#these commands will work on Windows or just use bash:
#https://msdn.microsoft.com/en-us/commandline/wsl/install_guide
#set AWS_ACCESS_KEY=$accesskey
#set AWS_SECRET_ACCESS_KEY=$secretkey
#set AWS_SESSION_TOKEN=$sessiontoken
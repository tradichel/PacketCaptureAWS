#!/bin/sh
#get our lambda ENI as we need to force a detachment
lambdaname=$1
count=$2
threshold=3 #try three times

if [ "$count" == "" ]; then count=0; fi
count=$(($count+1)) 
echo $count

echo "aws ec2 describe-network-interfaces --filter Name="requester-id",Values="*$lambdaname" > lambda-eni.txt  2>&1"
aws ec2 describe-network-interfaces --filter Name="requester-id",Values="*$lambdaname" > lambda-eni.txt  2>&1
attachmentid=$(./execute/get_value.sh lambda-eni.txt "AttachmentId")

if [ "$attachmentid" != "" ]; then
    echo "aws ec2 detach-network-interface --attachment-id $attachmentid --force"
    aws ec2 detach-network-interface --attachment-id $attachmentid --force

    #I don't see a good way to wait for the network interface to detach.
    #Pausing a few here and hope that works.
    SLEEP 8

    networkinterfaceid=$(./execute/get_value.sh lambda-eni.txt "NetworkInterfaceId")
    echo "aws ec2 delete-network-interface --network-interface-id $networkinterfaceid"
    output=$(aws ec2 delete-network-interface --network-interface-id $networkinterfaceid)

    #threshold reached
    if [ "$count" == "$threshold" ]; then return; fi
    
    #see if we have any more to delete
    ./execute/delete_lambda_eni.sh $lambdaname $count
    
fi

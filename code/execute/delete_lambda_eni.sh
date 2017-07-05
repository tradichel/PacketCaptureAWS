#!/bin/sh
#get our lambda ENI as we need to force a detachment
aws ec2 describe-network-interfaces --filter Name="requester-id",Values="*ConfigureFirebox" > lambda-eni.txt  2>&1
attachmentid=$(./execute/get_value.sh lambda-eni.txt "AttachmentId")
if [ "$attachmentid" != "" ]; then
    echo "aws ec2 detach-network-interface --attachment-id $attachmentid --force"
    aws ec2 detach-network-interface --attachment-id $attachmentid --force

    #I don't see a good way to wait for the network interface to detach.
    #Pausing a few here and hope that works.
    SLEEP 5

    networkinterfaceid=$(./execute/get_value.sh lambda-eni.txt "NetworkInterfaceId")
    echo "aws ec2 delete-network-interface --network-interface-id $networkinterfaceid"
    output=$(aws ec2 delete-network-interface --network-interface-id $networkinterfaceid)
    if [ "$output" != "" ]; then
        echo "If an error occurs deleting the network interface run the script again. Contacting AWS for a better solution..."
    fi
fi

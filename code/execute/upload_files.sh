#!/bin/sh
#note: If you want to see how the lambda.zip file was craeted, read this:
#http://websitenotebook.blogspot.com/2017/05/creating-paramiko-and-cryptography.html
keyname=$1

./execute/make_zip.sh



#upload the lambda code to the bucket used by lambda cloudformation file
bucket=$(./execute/get_output_value.sh "firebox-cli-s3bucket" "FireboxPrivateBucket")
aws s3 cp resources/firebox-lambda/fireboxconfig.zip s3://$bucket/fireboxconfig.zip --sse AES256 > upload.txt  2>&1  

error=$(cat upload.txt | grep "error\|Unknown")
if [ "$error" != "" ]; then
    echo "Error uploading fireboxconfig.zip: $error"; exit
fi

#upload bash script with cli commands
localfile=resources/firebox-lambda/configurefirebox.sh
remotefile=configurefirebox.sh
aws s3 cp $localfile s3://$bucket/$remotefile --sse AES256 > uploadsh.txt  2>&1  

error=$(cat upload.txt | grep "error\|Unknown\|path")
if [ "$error" != "" ]; then
    echo "Error uploading $localfile: $error"; exit
fi

#upload EC2 Key Pair
aws s3 cp $keyname.pem s3://$bucket/$keyname.pem --sse AES256 > upload.txt  2>&1  

error=$(cat upload.txt | grep "error\|Unknown\|path")
if [ "$error" != "" ]; then
    echo "Error uploading $keyname.pem: $error"; exit
fi
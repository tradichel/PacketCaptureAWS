#!/bin/sh
script="fireboxconfig.py"
#script="packetcapture.py"

#note: If you want to see how the lambda.zip file was craeted, read this:
#http://websitenotebook.blogspot.com/2017/05/creating-paramiko-and-cryptography.html
keyname=$1
#remove existing file
if [ -f ./resources/firebox-lambda/fireboxconfig.zip ]; then rm ./resources/firebox-lambda/fireboxconfig.zip; fi

#make a copy of lambda.zip
cp ./resources/firebox-lambda/lambda.zip ./resources/firebox-lambda/fireboxconfig.zip

#add py file to fireboxconfig.zip
zip -g -j ./resources/firebox-lambda/fireboxconfig.zip ./resources/firebox-lambda/$script

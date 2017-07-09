#!/bin/sh
script="fireboxconfig.py"
script2="fireboxsnat.py"
script3="fireboxcommands.py"

#remove existing file
if [ -f ./resources/firebox-lambda/fireboxconfig.zip ]; then rm ./resources/firebox-lambda/fireboxconfig.zip; fi

#make a copy of lambda.zip
cp ./resources/firebox-lambda/lambda.zip ./resources/firebox-lambda/fireboxconfig.zip

#add py files to fireboxconfig.zip
zip -g -j ./resources/firebox-lambda/fireboxconfig.zip ./resources/firebox-lambda/$script
zip -g -j ./resources/firebox-lambda/fireboxconfig.zip ./resources/firebox-lambda/$script2
zip -g -j ./resources/firebox-lambda/fireboxconfig.zip ./resources/firebox-lambda/$script3
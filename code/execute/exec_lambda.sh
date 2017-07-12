#!/bin/sh
functionname=$1

echo "* Run lambda function to configure firebox"
echo "* aws lambda invoke --function-name $functionname lambda-$functionname.txt"
aws lambda invoke --function-name $functionname lambda-$functionname.txt
echo "* lambda $functionname execution complete"
cat lambda-$functionname.txt
echo "* end of lambda $functionname logs"

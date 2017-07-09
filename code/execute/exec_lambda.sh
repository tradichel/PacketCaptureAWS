#!/bin/sh
functionname=$1

echo "* Run lambda function to configure firebox"
echo "* aws lambda invoke --function-name $functionname lambdalog.txt"
aws lambda invoke --function-name $functionname lambda-$functioname.txt
echo "* lambda $functionname execution complete"
cat lambda-$functioname.txt
echo "* end of lambda $functionname logs"

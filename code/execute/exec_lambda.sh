echo "* Run lambda function to configure firebox"
echo "* aws lambda invoke --function-name ConfigureFirebox lambdalog.txt"
aws lambda invoke --function-name ConfigureFirebox lambdalog.txt
echo ""
cat lambdalog.txt
echo ""
#temp while fixing
exit    
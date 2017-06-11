region=$1

if [ "$region" == "" ]; then
    echo "Region cannot be empty when retrieving S3 CIDRs in get_s3_ips.sh"
    exit
fi

#ugly script to get S3 cidr params. Want to re-write in a more readable programming language someday
#or get AWS to allow passing an array of strings and ports to create a list of network rules..
#or have an easy switch to add S3 cidrs to network lists for YUM updates...

#Note: In production setting you would want to monitor the 
#AWS IP ranges for changes and update the NACL rules if
#the CIDR blocks change.
s3ips=$(curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
python -c "import sys, json; ips = json.load(sys.stdin)['prefixes']; s3ips = [k['ip_prefix'].encode('ascii') for k in ips if k['service'] == 'S3' and k['region'] == '$region']; s3params = ['ParameterKey=params3cidr' + str(idx) + ',ParameterValue=' + item for idx, item in enumerate(s3ips)]; print (s3params)")

if [ "$region" != "us-east-1" ]; then
    s3eastips=$(curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
    python -c "import sys, json; ips = json.load(sys.stdin)['prefixes']; s3eastips = [k['ip_prefix'].encode('ascii') for k in ips if k['service'] == 'S3' and k['region'] == 'us-east-1']; s3eastparams = ['ParameterKey=params3eastcidr' + str(idx) + ',ParameterValue=' + item for idx, item in enumerate(s3eastips)]; print (s3eastparams)")
fi

s3ips="$s3ips $s3eastips"

echo $s3ips | sed -e 's/\[//g' -e 's/]//g' -e 's/, / /g' -e "s/'//g"
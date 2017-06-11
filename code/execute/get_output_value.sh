#!/bin/sh
stack=$1;key=$2;value=""

aws cloudformation describe-stacks --stack-name $stack > "$stack$key.txt" 2>&1 

if [ "$(cat $stack$key.txt | grep ValidationError)" != "" ]; then
	value=""
    break
else
	if [ "$(cat $stack$key.txt | grep error)" != "" ]; then
		value="$(cat $stack$key.txt | grep error)"
        break
	else
		value="$(cat $stack$key.txt | grep "\"OutputKey\": \"$key\"" -A1 | tail -n 1 | cut -d ':' -f 2- | sed -e 's/^[ \t]*//' -e 's/"//' -e 's/"//' -e 's/,//')"
	fi
fi

rm $stack$key.txt

echo $value

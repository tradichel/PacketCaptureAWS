#!/bin/sh
action=$1; stack=$2; template=$3; parameters=$4;
capabilities="--capabilities CAPABILITY_NAMED_IAM"

if [ "$stack" == "" ]; then
	echo "* Error: Stack name is required."; exit
fi 

if [ "$action" == "" ]; then
	echo "* Error: Action is required."; exit
fi

echo "***RUN TEMPLATE: $stack ***"

if [ "$action" == "delete" ]; then
	echo "* aws cloudformation delete-stack --stack-name $stack"
	aws cloudformation delete-stack --stack-name $stack > $stack.txt  2>&1
else
	if [ "$template" == "" ]; then
		echo "* Error: Stack template is required in parameter template in form file://filename"
		exit
	fi
	echo "* aws cloudformation $action-stack --stack-name $stack --template-body $template $capabilities $parameters"
	aws cloudformation $action-stack --stack-name $stack --template-body $template $capabilities $parameters > $stack.txt 2>&1
fi

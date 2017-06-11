action=$1; stack=$2
echo "* waiting for $stack to $action..."
aws cloudformation wait stack-$action-complete --stack-name $stack  >> $stack.txt  2>&1
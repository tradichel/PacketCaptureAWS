#!/bin/sh
action=$1;keyname=$2

echo "$action key $keyname"

aws ec2 describe-key-pairs --key-name $keyname > ec2key.txt  2>&1  
noexist=$(cat ec2key.txt | grep "does not exist")

if [ "$noexist" == "" ]
then
    if [ "$action" == "delete" ]; then
        aws ec2 delete-key-pair --key-name $keyname
        rm -f $keyname.pem
    fi
else
    if [ "$action" == "create" ]; then

        echo ""
        echo "* ---- NOTE --------------------------------------------"
        echo "* Creating EC2 keypair: $keyname"
        echo "* Do NOT check in keys to public source control systems."
        echo "* Keys are passwords. Protect them!"
        echo "* This github repository excludes .pem and .PEM files in the .gitignore file"
        echo "* https://git-scm.com/docs/gitignore"
        echo "* ------------------------------------------------------"
        echo ""
        
        aws ec2 create-key-pair --key-name $keyname --query 'KeyMaterial' --output text > $keyname.pem
        chmod 600 $keyname.pem
    fi
fi


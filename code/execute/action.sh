#!/bin/sh
action=$1; adminuser=$2; admincidr=$3; adminuserarn=$4; ami=$5; instancetype=$6; linuxami=$7

keyname="firebox-cli-ec2-key"
lambdafunction="ConfigureFirebox"

#gettig the S3 cidrs is a bit messy so separating this out and doing it 
#one time for all places it is required
s3cidrparams=$(./execute/get_s3_ips.sh $region)

#stack = file name less the .yaml extension
function modify_stack(){
    local action=$1;local config=$2;
    declare -a stackarray=("${!3}")
    for (( i = 0 ; i < ${#stackarray[@]} ; i++ ))
    do
        run_template "$action" "$config" "${stackarray[$i]}"
    done
}

function run_template () {
    local action=$1; local config=$2; local stack=$3;local parameters="";
 
    template="file://resources/firebox-$config/$stack.yaml"
    stackname="firebox-$config-$stack"
    exists=$(stack_exists $stackname)
    parameters=$(get_parameters $stack)
    action=$(validate_action "$exists" "$action" "$stackname" "$config")

    if [ "$action" == "noupdates" ]; then echo "$action"; return; fi
    
    if [ "$action" == "fail" ]; then
        ./execute/run_template.sh "delete" "$stackname" "$parameters"
        wait_to_complete "delete" $config $stackname
        action="create"
    fi

    ./execute/run_template.sh "$action" "$stackname" "$template" "$parameters"
   
   if [ -f $stackname.txt ]; then
        noupdates="$(cat $stackname.txt | grep 'No updates')"
        if [ "$noupdates" != "" ]; then echo "noupdates to stack"; return; fi

        err="$(cat $stackname.txt | grep 'error\|failed\|Error')"
        if [ "$err" != "" ]; then echo "$err"; exit; fi
        
        cat $stackname.txt
        wait_to_complete $action $config $stackname
    else
        echo "Something is amiss. Stack output file does not exist: $stackname.txt"
        exit
    fi
}

function stack_exists(){
    local stackname=$1
    aws cloudformation describe-stacks --stack-name $stackname > $stackname.txt  2>&1  
    exists=$(./execute/get_value.sh $stackname.txt "StackId")
    echo "$exists"
}

function get_parameters(){
    stack=$1
    stackparameter="--parameters ParameterKey=ParamStackName,ParameterValue=packet-capture-$stack"

    if [ "$stack" == "firebox" ]; then
        echo "$stackparameter ParameterKey=ParamKeyName,ParameterValue=$keyname ParameterKey=ParamFireboxAMI,ParameterValue=$ami ParameterKey=ParamInstanceType,ParameterValue=$instancetype ";return
    fi

    if [ "$stack" == "s3bucketpolicy" ]; then
        echo "$stackparameter ParameterKey=ParamAdminCidr,ParameterValue=$admincidr ParameterKey=ParamAdminUser,ParameterValue=$adminuser";return
    fi
 
    if [ "$stack" == "sgssh" ]; then
        echo "$stackparameter ParameterKey=ParamAdminCidr,ParameterValue=$admincidr";return
    fi

    if [ "$stack" == "sgpubliceni" ]; then

        #####
        #  
        #  Ports and Domain Names Used By WatchGuard Firebox as of 5/12/2017
        #  https://services.watchguard.com:TCP 443
        #  https://feedback.watchguard.com:TCP 443
        #  https://ask.watchguard.com:443 TCP
        #  tdr-fbla-eu.watchguard.com:4115 TCP
        #  tdr-fbla-na.watchguard.com:4115 TCP
        #  web.repauth.watchguard.com:53 UDP
        #
        #  NOTE: This code and security group template unfortunately
        #  make certain hard-coded assumptions. Should the number of IPs
        #  or domains change this script would need to be adjusted.
        #  It could also be written in a more robust way, possibly
        #  using a more up to date language. Additionally if the IPs
        #  themselves change then this firebox is open from an invalid IP 
        #  address, putting it at risk. So it would be better to monitor 
        #  for changes (or possibly for us to find a way to stablize these 
        #  IP addresses).
        #
        #  But for today, this works and this is just for initial testing.
        #
        ####

        parameters="$(get_ip_parameters 'services')"
        parameters="$parameters $(get_ip_parameters 'feedback')"
        parameters="$parameters $(get_ip_parameters 'ask')"
        parameters="$parameters $(get_ip_parameters 'tdr-fbla-eu')"
        parameters="$parameters $(get_ip_parameters 'tdr-fbla-na')"
        parameters="$parameters $(get_ip_parameters 'web.repauth')"
        
        echo "$stackparameter $parameters ParameterKey=ParamAdminCidr,ParameterValue=$admincidr"
        return

    fi 

    if [ "$stack" == "kmskey" ]; then
        echo "$stackparameter ParameterKey=ParamAdminUserArn,ParameterValue=$adminuserarn";return
    fi    

    if [ "$stack" == "s3endpointegress" ]; then
        #becuase we cannot use reference prefix lists dynamically
        #in cloudformation (as far as I can tell) need to use CLI
        #to get and pass into our S3 endpoint egress rule template
        aws ec2 describe-prefix-lists > prefixlist.txt  2>&1 
        prefixlistid=$(./execute/get_value.sh prefixlist.txt "PrefixListId")
        echo "$stackparameter ParameterKey=ParamPrefixListId,ParameterValue=$prefixlistid";return
    fi

    if [ "$stack" == "packetcaptureserver" ]; then
        echo "$stackparameter ParameterKey=ParamKeyName,ParameterValue=$keyname ParameterKey=ParamAmi,ParameterValue=$linuxami";return
    fi  

    if [ "$stack" == "webserver" ]; then
        echo "$stackparameter ParameterKey=ParamKeyName,ParameterValue=$keyname ParameterKey=ParamAmi,ParameterValue=$linuxami";return
    fi  

    #getting the S3 CIDRS is a bit messy. Putting that in a separate script
    if [ "$stack" == "sgs3cidrs" ]; then
        echo "$stackparameter $s3cidrparams";return
    fi

    if [ "$stack" == "sbpublic" ]; then
        echo "$stackparameter ParameterKey=ParamAdminCidr,ParameterValue=$admincidr $s3cidrparams";return
    fi

    if [ "$stack" == "sbmanagement" ] || [ "$stack" == "sbwebserver" ]; then
        echo "$stackparameter ParameterKey=ParamAdminCidr,ParameterValue=$admincidr $s3cidrparams";return
    fi

    if [ "$stack" == "lambda" ]; then
        echo "$stackparameter ParameterKey=ParamAdminCidr,ParameterValue=$admincidr";return
    fi

    echo "$stackparameter"
}

function get_ip_parameters(){
    name=$1;index=1;p=""
    ips=$(dig +short $name.watchguard.com | grep '^[1-9]')
    name=$(echo $name | sed -e 's/[.-]//g')
    for ip in $ips; do 
        p="$p ParameterKey=\"param$name$((index++))\",ParameterValue=\"$ip/32\""
    done
    echo $p
}

function validate_action(){
    local exists=$1;local action=$2;local stackname=$3;local config=$4;

    if [ "$action" == "delete" ]; then
        if [ "$exists" == "" ]; then action="noupdates"; fi
        echo $action
        return
    fi
    
    if [ "$exists" == "" ] && [ "$action" == "update" ]; then
        action="create"
    fi

    if [ "$exists" != "" ]; then 
        aws cloudformation describe-stacks --stack-name $stackname > $stackname.txt  2>&1  
        status=$(./execute/get_value.sh $stackname.txt "StackStatus")
        case "$status" in 
            ROLLBACK_COMPLETE|ROLLBACK_FAILED|DELETE_FAILED)
            action="fail"
            ;;
          *)
            action="update"
            ;;
          *)
        esac
    fi

    echo $action
}

function log_errors(){
    local stackname=$1;local action=$2

    aws cloudformation describe-stacks --stack-name $stackname > $stackname.txt  2>&1  
    exists=$(./execute/get_value.sh $stackname.txt "StackId")

    if [ "$exists" != "" ]; then

        aws cloudformation describe-stacks --stack-name $stackname > $stackname.txt  2>&1  
        status=$(./execute/get_value.sh $stackname.txt "StackStatus")
        echo "$stack status: $status"
        case "$status" in 
            UPDATE_COMPLETE|CREATE_COMPLETE)   
                return
                ;;
            *)
                cat $stackname.txt
                aws cloudformation describe-stack-events --stack-name $stackname | grep "ResourceStatusReason"
                echo "* ---- What's the problem? ---"
                echo "* Stack $action failed."
                echo "* See the details above which can also be found in the CloudFormation console"
                echo "* ----------------------------"
                exit
                ;;
          *)
        esac
    fi
}

function wait_to_complete () {
    local action=$1; local config=$2; local stack=$3
    ./execute/wait.sh $action $stack  
    log_errors $stack $action
}

#---Start of Script---#
if [ "$action" == "delete" ]; then

    ./execute/delete_files.sh

    stack=(
        "lambda"
        "kmskey"
    )

    modify_stack $action "lambda" stack[@] 

    stack=(
        "webserver"
        "packetcaptureserver"
    )

    modify_stack $action "instances" stack[@] 

    stack=(
        "s3endpointegress"
        "s3endpoint"
        "s3bucketpolicy"
        "clirole"
        "s3bucket"
     )

    modify_stack $action "cli" stack[@] 

    stack=(
        "flowlogs"
        "flowlogsrole"
        "elasticip"
        "firebox"
        "sgs3cidrs"
        "sgssh"
        "sgmanagementeni"
        "sgpubliceni"
        "sgwebservereni"
        "sbwebserver"
        "sgwebserver"
        "sbpublic"
        "sbmanagement"
        "routetables"
        "internetgateway"
        "vpc"
    )

    modify_stack $action "network" stack[@] 

    ./execute/keypair.sh $action $keyname

else #create/update

    ./execute/keypair.sh $action $keyname

    stack=(

        "vpc" 
        "internetgateway"
        "routetables"
        "sbwebserver"
        "sgwebservereni"
        "sgwebserver"
        "sbmanagement"
        "sgmanagement"
        "sbpublic"
        "sgpubliceni"
        "sgs3cidrs"
        "sgssh"
        "flowlogsrole" 
        "flowlogs"
        "firebox"
        "elasticip"
    )
    modify_stack $action "network" stack[@] 

    stack=(
        "s3bucket"
        "clirole"
        "s3endpoint"
        "s3bucketpolicy"
        "s3endpointegress"
    )
    modify_stack $action "cli" stack[@] 
    
    ./execute/upload_files.sh $keyname

    #first we need to delete the existing lambda to pick up updates
    action="delete"
    stack=(
        "lambda"
    )
    modify_stack $action "lambda" stack[@] 

    #then we can create or update the lambda
    action="create"
    stack=(
        "kmskey"
        "lambda"
    )
    modify_stack $action "lambda" stack[@] 

    ./execute/exec_lambda.sh
    
    stack=(
        "packetcaptureserver"
        "webserver"
    )

    modify_stack $action "instances" stack[@] 
    
fi



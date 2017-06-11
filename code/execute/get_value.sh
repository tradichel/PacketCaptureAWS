#!/bin/sh
filename=$1;key=$2; var=""
var="$(cat $filename | grep "\"$key\""  | cut -d ':' -f 2- | sed -e 's/^[ \t]*//' -e 's/"//' -e 's/"//' -e 's/,//')"
var="$(echo "${var}" | tr -d '[:space:]')"
echo "$var"
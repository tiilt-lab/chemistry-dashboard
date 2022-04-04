#!/usr/bin/env bash

file=$1

while IFS= read -r line
do
	for i in ${line//,/ }
	do
		python3 create_user_from.py $i
	done
done <"$file"

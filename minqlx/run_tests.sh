#!/bin/bash

for test_file in $(ls *_test.py)
do
  echo
  # echo -e "\x1B[92m>> ${test_file} <<\x1B[0m"
  echo -e "\x1B[0;01;32m>> ${test_file} <<\x1B[0m"
  python3 ${test_file}
done

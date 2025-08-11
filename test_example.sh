#!/bin/bash

# Example script for running local tests safely
# Copy this file and modify with your actual credentials

# Set your test DSN credentials here (do not commit to git!)
export TEST_DATABEND_DSN1='databend://username:password@host1:port/tpcds_100'
export TEST_DATABEND_DSN2='databend://username:password@host2:port/tpcds_100'

# Run the test
./test_local.sh
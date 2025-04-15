#!bin/bash

cwd = $(pwd)
# Take in the first argument to the script, check if its in ['smallboom', 'mediumboom', 'largeboom', 'megaboom']

# Define the allowed values
allowed_values=("smallboom" "mediumboom" "largeboom" "megaboom")

# Check if the first argument is in the allowed values
if [[ " ${allowed_values[@]} " =~ " $1 " ]]; then
    echo "Valid target: $1"
else
    echo "Invalid target. Allowed values are: ${allowed_values[*]}"
    exit 1
fi

# Next, check if the "pexs/logs-{target}" directory exists
if [ -d "pexs/logs-$1" ]; then
    echo "Directory pexs/logs-$1 exists."
else
    echo "Directory pexs/logs-$1 does not exist. Creating it now."
    cd pexs; unzip $1.zip;
    # Abort if the unzip fails
    if [ $? -ne 0 ]; then
        echo "Unzip failed. Aborting."
        exit 1
    fi
    cd ..
fi

# If the target is anything other than smallboom, git apply "patches/$1.patch"
if [ "$1" != "smallboom" ]; then
    echo "Applying patch for $1"
    git apply patches/$1.patch
    # Abort if the patch fails
    if [ $? -ne 0 ]; then
        echo "Patch failed. Aborting."
        exit 1
    fi
else
    echo "No patch needed for smallboom"
    git checkout boom
    # Abort if the checkout fails
    if [ $? -ne 0 ]; then
        echo "Checkout failed. Aborting."
        exit 1
    fi
fi

# Clear redis
echo "Clearing redis"
redis-cli -n 0 flushdb

echo "Target $1 prepared successfully."
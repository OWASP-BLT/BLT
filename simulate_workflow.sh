#!/bin/bash

# Simulate the user-controlled branch name (malicious payload)
BRANCH_NAME='test"; echo "PoC: Command Injection Detected" #'

# Simulate the vulnerable checkout step
echo "Simulating: actions/checkout@v4 with ref=$BRANCH_NAME"
echo "Command that would be executed: git checkout \"$BRANCH_NAME\""
eval "echo 'Executing: git checkout \"$BRANCH_NAME\"'"

# Simulate the vulnerable git push step
echo -e "\nSimulating: git push origin $BRANCH_NAME"
echo "Command that would be executed: git push origin \"$BRANCH_NAME\""
eval "echo 'Executing: git push origin \"$BRANCH_NAME\"'"

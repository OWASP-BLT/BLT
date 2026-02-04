#!/bin/bash

# Simulate the workflow logic for pull_request_target
echo "=== Simulating Improper Authorization in pull_request_target ==="

# Test Case 1: Spoofing as Dependabot
echo -e "\n[Test Case 1: Spoofing as Dependabot]"
export GITHUB_ACTOR="dependabot[bot]"
echo "github.actor = $GITHUB_ACTOR"

if [ "$GITHUB_ACTOR" == "dependabot[bot]" ]; then
  echo "⚠️ Auto-merge authorized for Dependabot! (Vulnerable)"
else
  echo "✅ Actor not authorized for auto-merge."
fi

# Test Case 2: Regular User (Not Dependabot)
echo -e "\n[Test Case 2: Regular User]"
export GITHUB_ACTOR="regular-user"
echo "github.actor = $GITHUB_ACTOR"

if [ "$GITHUB_ACTOR" == "dependabot[bot]" ]; then
  echo "⚠️ Auto-merge authorized for Dependabot! (Vulnerable)"
else
  echo "✅ Actor not authorized for auto-merge."
fi

# Test Case 3: Malicious User Spoofing Dependabot
echo -e "\n[Test Case 3: Malicious User Spoofing Dependabot]"
export GITHUB_ACTOR="dependabot[bot]"
echo "github.actor = $GITHUB_ACTOR (spoofed by malicious user)"

if [ "$GITHUB_ACTOR" == "dependabot[bot]" ]; then
  echo "⚠️ Auto-merge authorized for Dependabot! (Vulnerable - Spoofing Successful)"
else
  echo "✅ Actor not authorized for auto-merge."
fi

#!/bin/bash

NETWORK="intern_proj_default"

containers=("postgres" "redis" "kafka")

echo "🔍 Pinging containers on Docker network: $NETWORK"
echo "---------------------------------------------"

for c in "${containers[@]}"; do
  echo -n "Pinging $c ... "
  docker run --rm --network "$NETWORK" busybox ping -c 1 "$c" > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "reachable"
  else
    echo "unreachable"
  fi
done
#!/bin/bash

# Service hostnames and ports
POSTGRES_HOST="postgres"
POSTGRES_PORT=5432

REDIS_HOST="redis"
REDIS_PORT=6379

KAFKA_HOST="kafka"
KAFKA_PORT=9092

# Function to check TCP connectivity
check_connection() {
    local host=$1
    local port=$2
    nc -z -w3 $host $port >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "OK"
    else
        echo "FAIL"
    fi
}

echo "Checking inter-service connectivity..."

echo -n "Postgres -> Redis: "
check_connection $REDIS_HOST $REDIS_PORT

echo -n "Postgres -> Kafka: "
check_connection $KAFKA_HOST $KAFKA_PORT

echo -n "Redis -> Postgres: "
check_connection $POSTGRES_HOST $POSTGRES_PORT

echo -n "Redis -> Kafka: "
check_connection $KAFKA_HOST $KAFKA_PORT

echo -n "Kafka -> Postgres: "
check_connection $POSTGRES_HOST $POSTGRES_PORT

echo -n "Kafka -> Redis: "
check_connection $REDIS_HOST $REDIS_PORT

echo "Inter-service connectivity check complete."

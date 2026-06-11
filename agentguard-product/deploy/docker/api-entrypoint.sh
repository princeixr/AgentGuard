#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  chown -R agentguard:agentguard /data
  exec gosu agentguard "$@"
fi

exec "$@"

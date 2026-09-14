#!/bin/bash
# AL2023 postdeploy: run after docker compose is up (8080:8000).
set -euo pipefail
exec /opt/elasticbeanstalk/hooks/appdeploy/post/99_fix_nginx.sh

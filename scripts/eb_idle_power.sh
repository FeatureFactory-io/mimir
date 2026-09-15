#!/usr/bin/env bash
# Start or stop the *idle* Elastic Beanstalk env (the one that does not hold
# the prod CNAME). Never touches the live env.
#
# stop  — scale ASG to 0 so EB does not replace instances (saves compute + IPv4)
# start — scale ASG to 1 and wait until an instance is running (and optionally SSM)
#
# Required env:
#   EB_APP                    e.g. huginn
#   EB_ENV_A / EB_ENV_B       e.g. huginn-blue / huginn-green
#   PROD_CNAME_SUBSTRING      e.g. huginn-prod  (CNAME fragment that marks live)
#
# Optional:
#   AWS_DEFAULT_REGION        default us-east-1
#   EB_IDLE_WAIT_SSM=1        after start, wait until SSM lists the instance

set -euo pipefail

: "${EB_APP:?EB_APP not set}"
: "${EB_ENV_A:?EB_ENV_A not set}"
: "${EB_ENV_B:?EB_ENV_B not set}"
: "${PROD_CNAME_SUBSTRING:?PROD_CNAME_SUBSTRING not set}"

ACTION="${1:-}"
if [ "$ACTION" != "start" ] && [ "$ACTION" != "stop" ]; then
  echo "Usage: $0 start|stop" >&2
  exit 2
fi

AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_DEFAULT_REGION

_env_cname() {
  aws elasticbeanstalk describe-environments \
    --application-name "$EB_APP" \
    --environment-names "$1" \
    --query 'Environments[0].CNAME' --output text
}

_env_status() {
  aws elasticbeanstalk describe-environments \
    --application-name "$EB_APP" \
    --environment-names "$1" \
    --query 'Environments[0].Status' --output text
}

_instance_ids() {
  aws elasticbeanstalk describe-environment-resources \
    --environment-name "$1" \
    --query 'EnvironmentResources.Instances[*].Id' \
    --output text
}

_asg_name() {
  aws elasticbeanstalk describe-environment-resources \
    --environment-name "$1" \
    --query 'EnvironmentResources.AutoScalingGroups[0].Name' \
    --output text
}

_env_type() {
  aws elasticbeanstalk describe-configuration-settings \
    --application-name "$EB_APP" \
    --environment-name "$1" \
    --query "ConfigurationSettings[0].OptionSettings[?OptionName=='EnvironmentType'].Value | [0]" \
    --output text
}

# SingleInstance EB reverts MinSize=0 on the next reconcile. Drive the ASG
# directly and suspend Launch so it cannot replace the instance.
_force_asg_zero() {
  local env_name="$1"
  local asg ids
  asg="$(_asg_name "$env_name")"
  if [ -z "$asg" ] || [ "$asg" = "None" ]; then
    echo "No Auto Scaling group on ${env_name}"
    return 0
  fi
  echo "Suspending Launch/Replace on ASG ${asg} (SingleInstance cannot stay at MinSize=0 via EB)"
  aws autoscaling suspend-processes \
    --auto-scaling-group-name "$asg" \
    --scaling-processes Launch ReplaceUnhealthy HealthCheck AlarmNotification AZRebalance ScheduledActions \
    --output text >/dev/null
  aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name "$asg" \
    --min-size 0 --max-size 0 --desired-capacity 0 \
    --output text >/dev/null
  ids="$(_instance_ids "$env_name" || true)"
  if [ -n "$ids" ] && [ "$ids" != "None" ]; then
    echo "Terminating leftover instances via ASG: ${ids}"
    aws autoscaling terminate-instance-in-auto-scaling-group \
      --instance-id "$(echo "$ids" | awk '{print $1}')" \
      --should-decrement-desired-capacity \
      --output text >/dev/null
  fi
}

# Mirror of _force_asg_zero: stop drives ASG directly to 0/0/0, so start must
# drive ASG directly to 1/1/1. EB update-environment alone leaves desired=0.
_force_asg_one() {
  local env_name="$1"
  local asg
  asg="$(_asg_name "$env_name")"
  if [ -z "$asg" ] || [ "$asg" = "None" ]; then
    echo "No Auto Scaling group on ${env_name}"
    return 0
  fi
  echo "Scaling ASG ${asg} to MinSize=1 MaxSize=1 DesiredCapacity=1"
  _resume_asg "$env_name"
  aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name "$asg" \
    --min-size 1 --max-size 1 --desired-capacity 1 \
    --output text >/dev/null
}

_resume_asg() {
  local env_name="$1"
  local asg
  asg="$(_asg_name "$env_name")"
  if [ -z "$asg" ] || [ "$asg" = "None" ]; then
    return 0
  fi
  echo "Resuming ASG processes on ${asg}"
  aws autoscaling resume-processes --auto-scaling-group-name "$asg" --output text >/dev/null
}

_scale_asg() {
  local env_name="$1" min="$2" max="$3"
  echo "Scaling ${env_name} ASG MinSize=${min} MaxSize=${max}"
  aws elasticbeanstalk update-environment \
    --application-name "$EB_APP" \
    --environment-name "$env_name" \
    --option-settings \
      "Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=${min}" \
      "Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=${max}" \
    --output text >/dev/null
  echo "Waiting for ${env_name} to finish updating..."
  aws elasticbeanstalk wait environment-updated \
    --application-name "$EB_APP" \
    --environment-names "$env_name"
}

_wait_running_instance() {
  local env_name="$1"
  local i ids state
  for i in $(seq 1 40); do
    ids="$(_instance_ids "$env_name" || true)"
    if [ -n "$ids" ] && [ "$ids" != "None" ]; then
      state=$(aws ec2 describe-instances --instance-ids $ids \
        --query 'Reservations[].Instances[].State.Name' --output text)
      echo "  [${i}/40] instances=${ids} state=${state}"
      if echo "$state" | grep -q running; then
        return 0
      fi
    else
      echo "  [${i}/40] no instances yet (Status=$(_env_status "$env_name"))"
    fi
    sleep 15
  done
  echo "ERROR: ${env_name} has no running instance after start" >&2
  exit 1
}

_wait_ssm() {
  local ids="$1" i info
  echo "Waiting for SSM agent on ${ids}..."
  for i in $(seq 1 24); do
    info=$(aws ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=$(echo "$ids" | awk '{print $1}')" \
      --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || echo "None")
    echo "  [${i}/24] SSM PingStatus=${info}"
    if [ "$info" = "Online" ]; then
      return 0
    fi
    sleep 10
  done
  echo "ERROR: SSM agent not Online — backup/deploy would fail" >&2
  exit 1
}

_idle_already_runnable() {
  local env_name="$1"
  local ids state asg min max
  ids="$(_instance_ids "$env_name" || true)"
  if [ -z "$ids" ] || [ "$ids" = "None" ]; then
    return 1
  fi
  state=$(aws ec2 describe-instances --instance-ids $ids \
    --query 'Reservations[].Instances[].State.Name' --output text)
  echo "$state" | grep -q running || return 1
  asg="$(_asg_name "$env_name")"
  if [ -z "$asg" ] || [ "$asg" = "None" ]; then
    return 0
  fi
  read -r min max _ <<< "$(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names "$asg" \
    --query 'AutoScalingGroups[0].[MinSize,MaxSize,DesiredCapacity]' \
    --output text)"
  [ "${min:-0}" -ge 1 ] && [ "${max:-0}" -ge 1 ]
}

CNAME_A=$(_env_cname "$EB_ENV_A")
if echo "$CNAME_A" | grep -q "$PROD_CNAME_SUBSTRING"; then
  LIVE_ENV="$EB_ENV_A"
  IDLE_ENV="$EB_ENV_B"
else
  LIVE_ENV="$EB_ENV_B"
  IDLE_ENV="$EB_ENV_A"
fi

echo "Live env:  ${LIVE_ENV}  (holds ${PROD_CNAME_SUBSTRING} — will not ${ACTION})"
echo "Idle env:  ${IDLE_ENV}  ← ${ACTION}"

if [ "$ACTION" = "stop" ]; then
  ENV_TYPE="$(_env_type "$IDLE_ENV")"
  echo "Idle EnvironmentType=${ENV_TYPE}"
  if [ "$ENV_TYPE" = "LoadBalanced" ]; then
    _scale_asg "$IDLE_ENV" 0 0
  else
    _force_asg_zero "$IDLE_ENV"
  fi
  leftover="$(_instance_ids "$IDLE_ENV" || true)"
  if [ -n "$leftover" ] && [ "$leftover" != "None" ]; then
    echo "WARNING: leftover instances still registered on ${IDLE_ENV}: ${leftover}"
    echo "ASG terminate should have handled this; skipping ec2:TerminateInstances (not in mimir-ci IAM)."
  fi
  echo "IDLE STOP OK — ${IDLE_ENV} scaled to 0. Live ${LIVE_ENV} unchanged."
  exit 0
fi

if _idle_already_runnable "$IDLE_ENV"; then
  echo "Idle ${IDLE_ENV} already has a running instance at MinSize>=1 — skipping ASG scale"
else
  ENV_TYPE="$(_env_type "$IDLE_ENV")"
  echo "Idle EnvironmentType=${ENV_TYPE}"
  if [ "$ENV_TYPE" = "LoadBalanced" ]; then
    _scale_asg "$IDLE_ENV" 1 1
  else
    _force_asg_one "$IDLE_ENV"
  fi
  _wait_running_instance "$IDLE_ENV"
fi
RUNNING_IDS=$(_instance_ids "$IDLE_ENV")
if [ "${EB_IDLE_WAIT_SSM:-0}" = "1" ]; then
  _wait_ssm "$RUNNING_IDS"
fi
echo "IDLE START OK — ${IDLE_ENV} has running instance(s): ${RUNNING_IDS}"

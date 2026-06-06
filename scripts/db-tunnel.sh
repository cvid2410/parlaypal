#!/usr/bin/env bash
#
# db-tunnel.sh — open a local port-forward to the private prod RDS via the SSM bastion.
#
# The bastion (parlaypal-<env>-bastion) is defined in infra/comp.yml and managed by
# CloudFormation; its power state is "stop-when-idle" — this script starts it on demand
# and stops it when you're done so it costs ~$0.65/mo (EBS only) while idle.
#
# Nothing secret lives here: the script only opens the tunnel. You supply the DB password
# to psql / your GUI yourself (host=localhost, the rest is printed by `start`).
#
# Usage:
#   scripts/db-tunnel.sh start    # start bastion (if stopped), wait for SSM, open the tunnel (blocks)
#   scripts/db-tunnel.sh stop     # stop the bastion
#   scripts/db-tunnel.sh status   # show instance + SSM state
#
# Env overrides:
#   ENVIRONMENT   (default: prod)    -> picks bastion tag + RDS instance id
#   LOCAL_PORT    (default: 5432)    -> local port to bind (use 5433 if you run local pg)
#   AWS_REGION    (default: us-east-1)
#
set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:-prod}"
LOCAL_PORT="${LOCAL_PORT:-5432}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

BASTION_TAG="parlaypal-${ENVIRONMENT}-bastion"
DB_INSTANCE_ID="parlaypal-${ENVIRONMENT}"   # RDS DBInstanceIdentifier
REMOTE_PORT=5432

die() { echo "error: $*" >&2; exit 1; }

resolve_instance() {
  local id
  id=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=${BASTION_TAG}" \
                  "Name=instance-state-name,Values=running,stopped,stopping,pending" \
        --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null || true)
  [ -n "$id" ] && [ "$id" != "None" ] || die "no bastion found tagged ${BASTION_TAG}. Has comp-cd deployed it yet?"
  echo "$id"
}

resolve_rds_host() {
  aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" \
    --query 'DBInstances[0].Endpoint.Address' --output text 2>/dev/null \
    || die "could not resolve RDS endpoint for ${DB_INSTANCE_ID}"
}

cmd_start() {
  command -v session-manager-plugin >/dev/null 2>&1 \
    || die "session-manager-plugin not installed. Run: brew install --cask session-manager-plugin"

  local id state rds_host
  id=$(resolve_instance)

  state=$(aws ec2 describe-instances --instance-ids "$id" \
            --query 'Reservations[0].Instances[0].State.Name' --output text)
  if [ "$state" != "running" ]; then
    echo "starting bastion $id (was: $state) ..."
    aws ec2 start-instances --instance-ids "$id" >/dev/null
  else
    echo "bastion $id already running"
  fi

  echo -n "waiting for SSM to come Online"
  for _ in $(seq 1 30); do
    if [ "$(aws ssm describe-instance-information \
              --filters "Key=InstanceIds,Values=$id" \
              --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = "Online" ]; then
      echo " — online."
      break
    fi
    echo -n "."; sleep 5
  done

  rds_host=$(resolve_rds_host)
  cat <<EOF

tunnel ready — connect any client to:
  host: localhost   port: ${LOCAL_PORT}   db: ${ENVIRONMENT}   user: parlaypal
  psql: psql "postgresql://parlaypal:<password>@localhost:${LOCAL_PORT}/parlaypal"

(the password is the DB_PASSWORD secret; it is intentionally not stored in this script.)
Press Ctrl-C to close the tunnel, then: scripts/db-tunnel.sh stop

EOF

  exec aws ssm start-session --target "$id" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"host\":[\"${rds_host}\"],\"portNumber\":[\"${REMOTE_PORT}\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}"
}

cmd_stop() {
  local id
  id=$(resolve_instance)
  echo "stopping bastion $id ..."
  aws ec2 stop-instances --instance-ids "$id" \
    --query 'StoppingInstances[0].{id:InstanceId,state:CurrentState.Name}' --output table
}

cmd_status() {
  local id
  id=$(resolve_instance)
  local state ping
  state=$(aws ec2 describe-instances --instance-ids "$id" \
            --query 'Reservations[0].Instances[0].State.Name' --output text)
  ping=$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$id" \
          --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || echo "None")
  echo "bastion $id  ec2=$state  ssm=$ping"
}

case "${1:-}" in
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  *) echo "usage: $0 {start|stop|status}" >&2; exit 2 ;;
esac

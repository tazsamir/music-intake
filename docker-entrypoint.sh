#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  groupadd --non-unique --gid "$PGID" intake 2>/dev/null || true
  useradd --non-unique --uid "$PUID" --gid "$PGID" --home-dir /state --no-create-home intake 2>/dev/null || true
  chown "$PUID:$PGID" /state
  exec gosu "$PUID:$PGID" "$@"
fi
exec "$@"

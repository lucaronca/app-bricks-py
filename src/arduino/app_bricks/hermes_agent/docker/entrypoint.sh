#!/bin/sh
# Gateway entrypoint: wait for the app shim, configure Hermes, start the gateway.
set -eu

# The installer adds hermes to PATH via the shell rc; cover the common spots.
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc" 2>/dev/null || true
export PATH="$HOME/.local/bin:$HOME/.hermes/bin:$PATH"

if ! command -v hermes >/dev/null 2>&1; then
    echo "ERROR: 'hermes' CLI not found on PATH after install" >&2
    exit 1
fi

: "${HERMES_BOOTSTRAP_URL:=http://main:7181/bootstrap}"

echo "Waiting for app bootstrap at ${HERMES_BOOTSTRAP_URL} ..."
attempts=0
until curl -fsS "${HERMES_BOOTSTRAP_URL}" -o /tmp/hermes-bootstrap.json 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ $((attempts % 30)) -eq 0 ]; then
        echo "Still waiting for the app main container (${attempts}s)..."
    fi
    sleep 1
done
echo "Bootstrap payload received."

python3 /opt/hermes-brick/bootstrap.py /tmp/hermes-bootstrap.json

# Upstream README documents no web UI channel: without a messaging token the
# gateway has nothing to serve, so keep the container alive for the CLI channel.
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "No messaging token configured."
    echo "Chat with the agent via the CLI channel:"
    echo "  docker exec -it <app>-hermes-gateway-1 hermes"
    exec sleep infinity
fi

# TODO(hackathon): headless Telegram channel wiring (`hermes gateway setup`
# is interactive); verify the gateway picks the token up from ~/.hermes/.env.
exec hermes gateway start

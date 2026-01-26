#!/usr/bin/env bash
set -e

MODEL="$1"

if [ -z "$MODEL" ]; then
  echo "Usage: $0 <model>" >&2
  exit 1
fi

echo "Starting download..."
ollama serve 2>&1 &
OLLAMA_PID=$!

cleanup() {
  kill "$OLLAMA_PID" 2>/dev/null || true
  wait "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT

until ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "Pulling model: $MODEL"
ollama pull "$MODEL"

echo "Model pulled successfully."

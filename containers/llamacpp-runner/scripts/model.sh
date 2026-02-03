#!/usr/bin/env bash
set -e

CMD="$1"
ARG="$2"

usage() {
  echo "Usage:"
  echo "  $0 pull <model>"
  echo "  $0 rm <model>"
  exit 1
}

if [ -z "$CMD" ]; then
  usage
fi

case "$CMD" in
  pull)
    if [ -z "$ARG" ]; then
      usage
    else
      LD_LIBRARY_PATH=/usr/local/bin/ /usr/local/bin/llama-pull -dr "$ARG"
    fi
    ;;
  *)
    usage
    ;;
esac

echo "Done."

# Hermes gateway image for the arduino:hermes_agent brick.
#
# TODO(hackathon):
#   - Pin the Hermes release and verify the installer URL against the
#     upstream README (https://github.com/NousResearch/hermes-agent).
#   - If upstream publishes an official image, prefer `FROM` that image
#     and keep only the bootstrap layer here.
#   - Build & push: ghcr.io/arduino/app-bricks/hermes-gateway:0.1.0

FROM debian:bookworm-slim

# xz-utils: the installer downloads Node.js 22 as a .tar.xz and needs xz to extract it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git python3 xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Upstream one-line installer (verified 2026-07-24). As root it uses the FHS
# layout: code in /usr/local/lib/hermes-agent, binary /usr/local/bin/hermes,
# data /root/.hermes (matches the brick volume), own Node 22 in ~/.hermes/node.
# TODO(hackathon): add a version pin when upstream documents one.
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Pin the home/data location regardless of how the runtime user is resolved.
ENV HOME=/root HERMES_HOME=/root/.hermes

COPY bootstrap.py /opt/hermes-brick/bootstrap.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

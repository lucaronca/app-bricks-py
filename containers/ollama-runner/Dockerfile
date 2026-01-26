ARG REGISTRY
ARG OLLAMA_VERSION=v0.15.1

FROM ollama/ollama:${OLLAMA_VERSION} AS ollama-builder


FROM ${REGISTRY}app-bricks/base:latest AS production

COPY --from=ollama-builder /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-builder /usr/lib/ollama/libggml* /usr/lib/ollama/

COPY ./run.sh /

RUN set -ex; \
    chmod +x /usr/bin/ollama; \
    chmod +x /run.sh

# Ollama settings
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434
ENV OLLAMA_MODELS=/models

EXPOSE 11434

ENTRYPOINT ["/run.sh"]

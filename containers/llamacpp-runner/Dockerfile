FROM docker.io/ollama/ollama:latest AS ollama

FROM ubuntu:24.04 AS llamacpp-builder

# Install Dependencies
RUN export DEBIAN_FRONTEND=noninteractive; \
    apt update; \
    mkdir -p ~/dev/llm; \
    apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    ninja-build \
    ca-certificates \
    libgomp1 \
    libssl-dev:arm64 \
    && update-ca-certificates

RUN cd ~/dev/llm; \
    git clone https://github.com/ggml-org/llama.cpp; \
    cd llama.cpp; \
    # Build master, but we can switch to a specific commit if needed
    mkdir -p build; \
    cd build; \
    cmake .. -G Ninja \
		-DCMAKE_SYSTEM_NAME=Linux \
		-DCMAKE_SYSTEM_PROCESSOR=aarch64 \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_BUILD_TYPE=Release \
		-DGGML_NATIVE=OFF \
		-DLLAMA_BUILD_TESTS=OFF \
		-DGGML_BACKEND_DL=ON \
        # Disabling CPU repacking for compatibility issues
		-DGGML_USE_CPU_REPACK=OFF \
		-DGGML_CPU_ALL_VARIANTS=OFF; \
    ninja -j`nproc`

RUN cd ~/dev/llm/llama.cpp/build/; \
    mv bin bin-full; \
    mkdir -p bin; \
    cp bin-full/llama-cli bin/; \
    cp bin-full/llama-server bin/; \
    cp bin-full/lib* bin/

FROM ubuntu:24.04 AS production

COPY --from=llamacpp-builder /root/dev/llm/llama.cpp/build/bin /usr/local/bin/
COPY ./run.sh /

COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama/libggml-* /usr/lib/ollama/

RUN set -ex; \
    groupadd -g 44 video || true; \
    groupadd -g 993 render || true; \
    usermod -aG video ubuntu || true; \
    usermod -aG render ubuntu || true;

RUN export DEBIAN_FRONTEND=noninteractive; \
    apt update; \
    apt install --no-install-recommends -y curl libgomp1 ca-certificates; \
    update-ca-certificates; \
    apt autoremove -y; \
    apt dist-clean; \
    chmod +x /usr/local/bin/*; \
    chmod +x /usr/bin/ollama; \
    chmod +x /run.sh

# Environment variable setup

# Ollama settings
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434
ENV OLLAMA_MODELS=/models

# Llama.cpp server settings
ENV LLAMA_ARG_HOST=0.0.0.0
ENV LLAMA_ARG_PORT=9999
ENV LLAMA_ARG_MODELS_DIR=/models
ENV LLAMA_ARG_MODELS_MAX=4
#ENV LLAMA_ARG_THREADS=4
#ENV LLAMA_API_KEY=key

ENTRYPOINT ["./run.sh"]

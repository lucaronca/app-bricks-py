ARG REGISTRY

FROM debian:trixie AS llamacpp-builder

ENV LLAMA_CPP_VERSION=b7818

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
    git checkout ${LLAMA_CPP_VERSION}; \
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
        # Enabling CPU repacking for compatibility issues
		-DGGML_USE_CPU_REPACK=ON \
		-DGGML_CPU_ALL_VARIANTS=OFF; \
    ninja -j`nproc`

RUN cd ~/dev/llm/llama.cpp/build/; \
    mv bin bin-full; \
    mkdir -p bin; \
    cp bin-full/llama-cli bin/; \
    cp bin-full/llama-server bin/; \
    cp bin-full/lib* bin/

FROM ${REGISTRY}app-bricks/base:latest AS production

COPY --from=llamacpp-builder /root/dev/llm/llama.cpp/build/bin /usr/local/bin/
COPY ./run.sh /

RUN set -ex; \
    groupadd -g 44 video || true; \
    groupadd -g 993 render || true; \
    usermod -aG video ubuntu || true; \
    usermod -aG render ubuntu || true; \
    chmod +x /usr/local/bin/*; \
    chmod +x /run.sh

EXPOSE 9999

USER arduino

ENV HOME=/home/arduino
ENV USER=arduino

ENTRYPOINT ["/run.sh"]

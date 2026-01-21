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

RUN set -ex; \
    groupadd -g 44 video || true; \
    groupadd -g 993 render || true; \
    usermod -aG video ubuntu || true; \
    usermod -aG render ubuntu || true;

RUN export DEBIAN_FRONTEND=noninteractive; \
    apt update; \
    apt install --no-install-recommends -y curl libgomp1; \
    apt autoremove -y; \
    apt dist-clean; \
    chmod +x /usr/local/bin/*; \
    chmod +x /run.sh

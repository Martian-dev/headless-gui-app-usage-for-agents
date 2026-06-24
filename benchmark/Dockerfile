FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-lc"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    fluxbox \
    libreoffice-writer \
    python3 \
    python3-yaml \
    ripgrep \
    scrot \
    x11vnc \
    xdotool \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

ENV NVM_DIR=/usr/local/nvm
RUN mkdir -p "$NVM_DIR" \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash \
    && source "$NVM_DIR/nvm.sh" \
    && nvm install 22 \
    && nvm alias default 22 \
    && npm install -g @openai/codex@0.139.0 \
    && ln -sf "$NVM_DIR/versions/node/$(nvm version)/bin/node" /usr/local/bin/node \
    && ln -sf "$NVM_DIR/versions/node/$(nvm version)/bin/npm" /usr/local/bin/npm \
    && ln -sf "$NVM_DIR/versions/node/$(nvm version)/bin/codex" /usr/local/bin/codex \
    && codex --version

WORKDIR /workspace
COPY . /workspace/benchmark

ENV DISPLAY=:99

CMD ["python3", "/workspace/benchmark/runner.py", "--task", "/workspace/benchmark/tasks/task001.yaml", "--mode", "codex-agent"]

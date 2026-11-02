# Linux image of the web app (SPA + API + job worker) for a future vendor move.
# The home-server beta runs natively (docs/webapp-architecture-decision.md §25, H7);
# CI builds this image on every PR so Linux portability stays honest.
# macOS-only features (tab reading, AppleScript store reads) stay off here.

FROM node:22-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates util-linux \
    && rm -rf /var/lib/apt/lists/*
# Litestream (offsite replication, §25.4 step 8), pinned + SHA-256 checked — the same
# version deploy/macos/install.sh installs. Unused unless MM_OFFSITE_URL is configured:
# the vendor move restores with `mm host restore --data-dir /data`, then runs
# `mm host replicate --exec "mm serve --host 0.0.0.0 --port 8765"` (docs/home-server.md).
ARG LITESTREAM_VERSION=0.5.17
ARG TARGETARCH
RUN set -eu; \
    case "${TARGETARCH:-amd64}" in \
      amd64) arch=x86_64; sha=cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d ;; \
      arm64) arch=arm64; sha=f8ca4a050095c1efbda2c4365172e61bf9d955ea0d9ac42f448b52e51819baa5 ;; \
      *) echo "no pinned Litestream for ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    mkdir -p /usr/local/src/litestream; cd /usr/local/src/litestream; \
    curl -fsSL --proto '=https' -o ls.tgz "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-${arch}.tar.gz"; \
    echo "${sha}  ls.tgz" | sha256sum -c -; \
    tar -xzf ls.tgz litestream; install -m 0755 litestream /usr/local/bin/litestream; \
    cd /; rm -rf /usr/local/src/litestream; \
    test "$(litestream version)" = "${LITESTREAM_VERSION}"
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/ src/
COPY scripts/ scripts/
COPY config/ config/
COPY .claude/skills/ .claude/skills/
RUN uv sync --locked --no-dev
COPY --from=web /app/web/dist web/dist
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown -R app:app /app /data
USER app

ENV MAGIC_MANAGER_DB=/data/magic_manager.db
VOLUME /data
EXPOSE 8765
CMD ["uv", "run", "--frozen", "--no-dev", "mm", "serve", "--host", "0.0.0.0", "--port", "8765"]

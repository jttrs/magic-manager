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
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY src/ src/
COPY scripts/ scripts/
COPY config/ config/
COPY .claude/skills/ .claude/skills/
RUN uv sync --no-dev
COPY --from=web /app/web/dist web/dist

ENV MAGIC_MANAGER_DB=/data/magic_manager.db
VOLUME /data
EXPOSE 8765
CMD ["uv", "run", "--no-dev", "mm", "serve", "--host", "0.0.0.0", "--port", "8765"]

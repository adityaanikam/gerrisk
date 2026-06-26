# ─── Stage 1: deps ────────────────────────────────────────────────────────────
# Install Node + Python dependencies in a separate layer so the final image
# only needs to copy the built artefacts and the installed packages.
#
# Build context is the repo ROOT (set in docker-compose.yml).
# The Next.js app lives in geririsk-ai/; requirements.txt lives at the root.

FROM node:18-alpine AS deps

# Install Python 3, pip, and build toolchain needed by some pip packages
RUN apk add --no-cache \
        python3 \
        py3-pip \
        python3-dev \
        gcc \
        musl-dev \
        libffi-dev \
        openssl-dev

WORKDIR /app

# ── Python dependencies ──────────────────────────────────────────────────────
# requirements.txt is at the repo root (the build context root)
COPY requirements.txt ./requirements.txt

RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Node dependencies ────────────────────────────────────────────────────────
# package files are inside geririsk-ai/
COPY geririsk-ai/package.json geririsk-ai/package-lock.json ./

RUN npm ci


# ─── Stage 2: builder ─────────────────────────────────────────────────────────
FROM node:18-alpine AS builder

RUN apk add --no-cache python3

WORKDIR /app

# Bring in installed node_modules and Python venv from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/.venv /app/.venv

# Copy the entire Next.js source tree (context root → geririsk-ai/)
COPY geririsk-ai/ .

# Copy Python ML module (also inside geririsk-ai/ml)
# (Already included by the line above; listed explicitly for clarity)

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# ─── Stage 3: runner (final image) ────────────────────────────────────────────
FROM node:18-alpine AS runner

LABEL maintainer="GeriRisk AI"
LABEL description="GeriRisk Next.js app with embedded Python ML runtime"

# Install only the Python runtime — no build tools needed in the final image
RUN apk add --no-cache python3

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Copy the self-contained Next.js standalone bundle
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static     ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public           ./public

# Copy the ML module (predict.py + models/)
COPY --from=builder --chown=nextjs:nodejs /app/ml ./ml

# Copy the Python virtualenv with all installed packages
COPY --from=deps    --chown=nextjs:nodejs /app/.venv /app/.venv

# Put the venv's python/pip on PATH so child_process.spawn("python", ...) works
ENV PATH="/app/.venv/bin:$PATH"

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# The standalone build emits server.js at the root of the standalone dir
CMD ["node", "server.js"]

# --- deps: install dependencies only ---------------------------------
# A separate stage purely so Docker's layer cache can skip `npm ci`
# entirely on a rebuild triggered by a SOURCE change — only a change to
# package.json/package-lock.json invalidates this layer, same reasoning
# as the backend Dockerfile copying requirements.txt before the rest of
# the source.
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- builder: compile the production build ----------------------------
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* variables are inlined into the CLIENT bundle at BUILD
# time — Next.js does not read them at container startup the way a
# normal environment variable works. Passing this as a build ARG (not
# just an ENV in the final image) is what actually lets a real
# deployment bake in its real backend URL; setting it only at `docker
# run` time would silently have no effect on the already-built bundle.
# Defaults to the docker-compose dev value (see docker-compose.yml) —
# the backend's port is published to the HOST there, and the browser
# (unlike this build step) runs on the host, not inside the Docker
# network, so "localhost:8000" is genuinely correct for that case, not
# a placeholder.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# --- runner: the actual production image -------------------------------
# Deliberately FROM a fresh node:20-alpine, not `FROM builder` — the
# whole point of a multi-stage build is that node_modules, the full
# source tree, and every build-time tool (webpack, the TypeScript
# compiler) never exist in this final image at all. Only what
# output:"standalone" (next.config.ts) actually traced as needed at
# runtime gets copied in below.
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# A dedicated, unprivileged user — never run a production Node process
# as root, even inside a container that's already namespace-isolated.
# Matches Next.js's own official Docker deployment example.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Static assets Next.js does NOT include in the standalone trace by
# design (see next.config.ts's comment / the Next.js docs on `output`)
# — served directly by the standalone server.js below once present at
# these exact paths.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Hits the app's own root route — cheap, always-available, no auth
# required, the same reasoning as the backend's GET /health existing at
# all. Uses Node's built-in fetch (Node 20+, no curl/wget needed in this
# minimal alpine image, which deliberately doesn't have either).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

# server.js is the minimal production server output:"standalone"
# generates — not `next start`, which would require the full
# node_modules tree this image deliberately doesn't have.
CMD ["node", "server.js"]

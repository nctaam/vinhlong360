FROM node:22-alpine AS deps

WORKDIR /app/web-nuxt
COPY web-nuxt/package*.json ./
RUN npm ci

FROM node:22-alpine AS build

WORKDIR /app/web-nuxt
COPY --from=deps /app/web-nuxt/node_modules ./node_modules
COPY web-nuxt/ ./
COPY config/ /app/config/
RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app/web-nuxt
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

COPY --from=build /app/web-nuxt/.output ./.output

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]

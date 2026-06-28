#!/usr/bin/env bash
# scripts/setup_monitoring.sh — Generate monitoring stack configs
# (Prometheus + Grafana + Loki + Promtail) for vinhlong360.
#
# Creates/overwrites config files in scripts/monitoring/ and prints
# docker-compose integration instructions.
#
# Works on Linux and Git Bash on Windows.
#
# Usage:
#   scripts/setup_monitoring.sh              # generate all configs
#   scripts/setup_monitoring.sh --print-only # only print docker-compose snippet

set -euo pipefail

# --- Resolve repo root (portable: works on Linux + Git Bash) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITORING_DIR="$ROOT/scripts/monitoring"

PRINT_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --print-only) PRINT_ONLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--print-only]"
      echo "  Generates monitoring configs in scripts/monitoring/"
      echo "  --print-only  Only print docker-compose snippet, don't write files"
      exit 0
      ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if [ "$PRINT_ONLY" = 0 ]; then
  mkdir -p "$MONITORING_DIR"
  echo "==> generating monitoring configs in $MONITORING_DIR"

  # --- prometheus.yml ---
  cat > "$MONITORING_DIR/prometheus.yml" <<'PROMEOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'vl360-agent'
    static_configs:
      - targets: ['agent:8360']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
PROMEOF
  echo "  wrote prometheus.yml"

  # --- grafana datasource provisioning ---
  cat > "$MONITORING_DIR/grafana-datasources.yml" <<'GRAFEOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
GRAFEOF
  echo "  wrote grafana-datasources.yml"

  # --- loki-config.yml ---
  cat > "$MONITORING_DIR/loki-config.yml" <<'LOKIEOF'
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h
LOKIEOF
  echo "  wrote loki-config.yml (30-day retention)"

  # --- promtail-config.yml ---
  cat > "$MONITORING_DIR/promtail-config.yml" <<'PTEOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    static_configs:
      - targets:
          - localhost
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*-json.log
    pipeline_stages:
      - docker: {}
      - match:
          selector: '{job="docker"}'
          stages:
            - json:
                expressions:
                  tag: tag
            - labels:
                tag:
PTEOF
  echo "  wrote promtail-config.yml"

  echo "==> all monitoring configs generated"
fi

# --- Print docker-compose integration instructions ---
echo ""
echo "============================================================"
echo "  Docker Compose integration for monitoring stack"
echo "============================================================"
echo ""
echo "Add the following services to your docker-compose.yml"
echo "(or create a docker-compose.monitoring.yml):"
echo ""
cat <<'COMPOSE'
  # --- Monitoring stack ---
  prometheus:
    image: prom/prometheus:latest
    container_name: vl360-prometheus
    volumes:
      - ./scripts/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - vl360-net

  grafana:
    image: grafana/grafana:latest
    container_name: vl360-grafana
    volumes:
      - ./scripts/monitoring/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    networks:
      - vl360-net

  loki:
    image: grafana/loki:latest
    container_name: vl360-loki
    volumes:
      - ./scripts/monitoring/loki-config.yml:/etc/loki/local-config.yml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yml
    ports:
      - "3100:3100"
    restart: unless-stopped
    networks:
      - vl360-net

  promtail:
    image: grafana/promtail:latest
    container_name: vl360-promtail
    volumes:
      - ./scripts/monitoring/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped
    networks:
      - vl360-net
    depends_on:
      - loki

  node-exporter:
    image: prom/node-exporter:latest
    container_name: vl360-node-exporter
    ports:
      - "9100:9100"
    restart: unless-stopped
    networks:
      - vl360-net

# Add to volumes section:
volumes:
  prometheus_data:
  grafana_data:
  loki_data:
COMPOSE

echo ""
echo "Quick start:"
echo "  # Start monitoring stack alongside existing services:"
echo "  docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d"
echo ""
echo "  # Or if added to main docker-compose.yml:"
echo "  docker compose up -d prometheus grafana loki promtail node-exporter"
echo ""
echo "Access:"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3001 (admin / \$GRAFANA_PASSWORD or 'admin')"
echo "  Loki:       http://localhost:3100 (via Grafana Explore)"
echo ""
echo "Note: Ensure the vl360-agent service exposes /metrics on port 8360."
echo "      Grafana port is 3001 to avoid conflict with Nuxt (port 3000)."
echo "============================================================"

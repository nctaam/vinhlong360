# Monitoring Setup — vinhlong360

## Health Endpoint

```
GET /health → 200 {"status": "ok", "features": {...}}
```

Backend health check returns feature flag status. Use this as the primary probe.

## UptimeRobot (Free Tier)

1. Tạo tài khoản tại https://uptimerobot.com (miễn phí 50 monitors)
2. Thêm monitor:
   - **Type:** HTTP(S)
   - **URL:** `https://vinhlong360.vn/health`
   - **Interval:** 5 phút
   - **Alert contacts:** Telegram bot (xem bên dưới)

## Telegram Alert

1. Tạo bot qua @BotFather → lưu token
2. Tạo group/channel, thêm bot
3. Lấy chat_id: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Trong UptimeRobot: **My Settings → Alert Contacts → Add → Telegram**
   - Bot Token + Chat ID

## Docker Health Checks

Đã cấu hình trong `docker-compose.yml`:

| Service  | Check                              | Interval |
|----------|-------------------------------------|----------|
| postgres | `pg_isready -U vl360`              | 10s      |
| redis    | `redis-cli ping`                    | 10s      |
| agent    | `curl -f http://localhost:8360/health` | 30s   |
| nuxt     | `wget -qO- http://localhost:3000/`  | 30s      |

Docker tự restart container khi healthcheck fail (policy: `unless-stopped`).

## Log Monitoring

Production log rotation đã cấu hình trong `docker-compose.prod.yml`:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Xem log:
```bash
docker compose logs -f agent --tail 100
docker compose logs -f nuxt --tail 100
docker compose logs -f nginx --tail 100
```

Tìm lỗi:
```bash
docker compose logs agent 2>&1 | grep -i error
```

## Resource Monitoring

Xem resource usage real-time:
```bash
docker stats
```

Limits đã set trong `docker-compose.prod.yml`:

| Service  | Memory | CPU  |
|----------|--------|------|
| postgres | 512M   | 1.0  |
| redis    | 128M   | 0.5  |
| agent    | 1G     | 2.0  |
| bot-gw   | 256M   | 0.5  |
| nuxt     | 512M   | 1.0  |

## Disk Usage

Kiểm tra định kỳ:
```bash
df -h
du -sh /var/lib/docker/volumes/*
```

Alert khi disk > 80%: thêm cron job:
```bash
# /etc/cron.d/disk-alert
0 */6 * * * root [ $(df / --output=pcent | tail -1 | tr -d ' %') -gt 80 ] && curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=DISK+ALERT:+$(hostname)+$(df+/+--output=pcent|tail+-1)"
```

## SSL Certificate Expiry

Let's Encrypt cert tự renew qua certbot timer. Kiểm tra:
```bash
certbot certificates
openssl s_client -connect vinhlong360.vn:443 2>/dev/null | openssl x509 -noout -dates
```

UptimeRobot cũng check SSL expiry tự động (alert 14 ngày trước).

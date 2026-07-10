# Hướng dẫn chạy Session Song Song
> STATUS (2026-07-10): active — hướng dẫn chạy session song song, tham chiếu.


> Rút kinh nghiệm từ đợt 3 session (2026-06-27): 228 commits, 1 conflict CLAUDE.md, 1 crash prod do JWT_SECRET.

---

## 1. Chuẩn bị prompt — 5 khắc phục bắt buộc

### KP1. CLAUDE.md — KHÔNG ghi đè

**Vấn đề:** Mỗi session thay CLAUDE.md bằng scoped version → conflict khi merge → phải restore thủ công.

**Giải pháp:** Đặt scope rules VÀO PROMPT, không tạo file CLAUDE.md riêng.

```
# TRONG PROMPT cho session (thay vì tạo CLAUDE.md scoped):

## Phạm vi file (TUYỆT ĐỐI)
ĐƯỢC sửa: [danh sách dirs]
KHÔNG ĐƯỢC sửa: [danh sách dirs]
KHÔNG SỬA file: CLAUDE.md, .env.example, docker-compose.yml, .gitignore

## Commit
Branch: session-xx (đã checkout)
Format: [XX] <mô tả>
KHÔNG push, KHÔNG merge
```

### KP2. Env vars prod — liệt kê trong prompt

**Vấn đề:** Session-BE thêm `JWT_SECRET` vào required config mà VPS chưa có → crash.

**Giải pháp:** Prompt phải chứa danh sách env vars hiện tại trên prod.

```
# TRONG PROMPT cho session-BE:

## Biến môi trường HIỆN CÓ trên VPS prod
(session KHÔNG ĐƯỢC thêm required check cho biến NGOÀI danh sách này)

ADMIN_API_KEY, AGENT_URL, AUTONOMOUS_AGENT_ENABLED,
BACKGROUND_INDEX_BUILD, BUILD_SEARCH_INDEXES, CORS_ORIGINS,
DATABASE_URL, DESTRUCTIVE_OPS_LOCKED, ENVIRONMENT,
LLM_API_KEY, LLM_BASE_URL, LLM_TIMEOUT, LOG_LEVEL,
R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, SITE_URL,
SCHEDULER_ENABLE_AUTONOMOUS_TASKS,
TELEGRAM_BOT_TOKEN, ZALO_OA_ACCESS_TOKEN, ZALO_OA_SECRET

Nếu cần biến mới trên prod:
- Ghi vào .env.example VỚI giá trị mặc định an toàn (rỗng/false)
- KHÔNG thêm vào danh sách required trong config validator
- Ghi note ở cuối commit: "DEPLOY NOTE: cần thêm XYZ vào .env prod"
```

Cách lấy danh sách env vars mới nhất:
```bash
ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202 \
  "grep -E '^[A-Z]' /opt/vinhlong360/.env | cut -d= -f1 | sort -u"
```

### KP3. Giới hạn scope rõ ràng — KHÔNG open-ended

**Vấn đề:** Session-BE nhận prompt kiểu "nâng cấp security" → tự mở rộng scope vô hạn (130 commits, lặp nhiều pattern).

**Giải pháp:** Mỗi session tối đa **5-10 task cụ thể**, có verify riêng.

```
# TRONG PROMPT:

## Tasks (làm ĐÚNG THỨ TỰ, KHÔNG tự thêm)

1. [Tên task cụ thể]
   - File: path/to/file.py
   - Làm gì: [mô tả 2-3 dòng]
   - Verify: [lệnh kiểm tra]

2. [Tên task cụ thể]
   ...

SAU KHI XONG 5 TASK: DỪNG. Không tự tìm thêm việc.
Nếu phát hiện issue khác → ghi vào commit message cuối cùng,
KHÔNG tự sửa.
```

### KP4. Integration contract — API spec giữa FE/BE

**Vấn đề:** FE gọi endpoint mới mà BE chưa implement đúng format, hoặc ngược lại.

**Giải pháp:** Viết API contract vào prompt CẢ 2 session FE và BE.

```
# TRONG PROMPT cho CẢ session-FE và session-BE:

## API Contract (hai session phải khớp)

### GET /api/map-pins
Response: { pins: [{ id, name, lat, lng, type, thumbnail? }] }

### GET /api/entities/{id}/review-stats
Response: { avg, count, distribution: {1:n, 2:n, ...}, categories: [...] }

### GET /api/entities/{id}/gallery
Response: { images: [{ url, caption?, source? }] }

FE gọi đúng format này. BE trả đúng format này.
Không tự đổi field name hoặc thêm field ngoài spec.
```

### KP5. Checklist merge — chạy script trước

**Vấn đề:** Merge rồi deploy mới phát hiện lỗi, phải hotfix trên prod.

**Giải pháp:** Chạy `pre_merge_check.py` + integration test sau merge.

```bash
# TRƯỚC merge:
python scripts/pre_merge_check.py session-fe session-be session-content

# Merge từng branch:
git merge session-be --no-edit
git merge session-fe --no-edit
git merge session-content --no-edit

# Restore CLAUDE.md nếu bị đè:
git show <commit-trước-sessions>:CLAUDE.md > CLAUDE.md
git add CLAUDE.md && git commit -m "Restore original CLAUDE.md"

# SAU merge — integration check:
python -m pytest -q                    # backend tests xanh
cd web-nuxt && npm run build           # frontend build pass
# Khởi động local để smoke test (nếu cần):
$env:BUILD_SEARCH_INDEXES='false'; python agent/server.py
```

---

## 2. Quy trình đầy đủ

### Bước 1: Chuẩn bị (10 phút)

```bash
# Lấy env vars prod (cho KP2)
ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202 \
  "grep -E '^[A-Z]' /opt/vinhlong360/.env | cut -d= -f1 | sort -u"

# Tạo branches
git checkout main
git checkout -b session-fe
git checkout main && git checkout -b session-be
git checkout main && git checkout -b session-content
git checkout main
```

### Bước 2: Viết prompt (mỗi session)

Theo template ở **Appendix A** (cuối file này):
- Bối cảnh chung (copy từ CLAUDE.md §0)
- Phạm vi file (KP1)
- Env vars prod (KP2, chỉ session-BE)
- 5-10 tasks cụ thể (KP3)
- API contract (KP4, cho FE+BE)
- Verify steps

### Bước 3: Chạy sessions

Mở 3 session, paste prompt, để chạy.

### Bước 4: Pre-merge check

```bash
python scripts/pre_merge_check.py session-fe session-be session-content
```

Fix mọi CRITICAL trước khi merge.

### Bước 5: Merge + verify

```bash
git checkout main
git merge session-be --no-edit
git merge session-fe --no-edit
git merge session-content --no-edit

# Restore CLAUDE.md
git show <base-commit>:CLAUDE.md > CLAUDE.md
git add CLAUDE.md && git commit -m "Restore CLAUDE.md after session merges"

# Verify
python -m pytest -q
cd web-nuxt && npm run build
```

### Bước 6: Deploy

```bash
bash scripts/deploy.sh --all --skip-build  # hoặc --replace nếu data thay đổi
```

---

## 3. Quyết định khi nào dùng song song vs tuần tự

| Tình huống | Nên dùng | Lý do |
|---|---|---|
| FE + BE + Content riêng biệt | Song song 3 | File isolation 100% |
| 2+ tasks cùng sửa `server.py` | Tuần tự | Conflict chắc chắn |
| Refactor cross-cutting (rename API) | Tuần tự | FE+BE phải đồng bộ |
| Data migration + code dùng data mới | Tuần tự | Code phụ thuộc data format |
| Research/audit + implement | Song song 2 | Không chia sẻ file |
| Nhiều page FE độc lập | Song song 2-3 | Mỗi session 1 nhóm page |

---

## 4. Anti-patterns (TRÁNH)

1. **Prompt open-ended** ("nâng cấp security toàn bộ") → session tự mở rộng vô hạn
2. **Để session tạo CLAUDE.md riêng** → conflict mỗi lần merge
3. **Không liệt kê env vars prod** → session thêm required check → crash
4. **Merge rồi deploy luôn** → không catch integration issues
5. **Tất cả session cùng loại** (3 FE) → conflict cao, throughput thấp

---

## Appendix A: Prompt Templates

> Copy phần tương ứng, điền `{{placeholder}}`, paste vào session mới.
> Mỗi session PHẢI có đủ 7 section: Bối cảnh, Phạm vi, Env vars (BE), Tasks, API Contract, Verify, Dừng khi nào.

### Template chung (đầu mỗi prompt)

```
## Bối cảnh

Dự án vinhlong360: MXH du lịch/OCOP/cộng đồng cho Vĩnh Long (tỉnh mới sáp nhập VL+BT+TV).
Solo dev, web-first, Nuxt 4 SSR, budget <1tr/tháng.
Mô hình "CHỈ GIỚI THIỆU" — KHÔNG booking/thanh toán (§1.4 CLAUDE.md). CTA chỉ Zalo/Gọi điện.
Backend FastAPI (`agent/`) + frontend Nuxt 4 SSR (`web-nuxt/`).
DB: SQLite (knowledge) + Postgres (UGC/auth).

Đọc CLAUDE.md §1-§6 để hiểu ràng buộc kiến trúc.
Đọc docs/implementation-specs.md để biết specs cần implement.
{{THÊM CONTEXT ĐẶC THÙ CHO ĐỢT NÀY}}
```

### Session FE template

```
## Phạm vi file (TUYỆT ĐỐI — vi phạm = hỏng merge)

ĐƯỢC sửa: web-nuxt/{pages,components,composables,layouts,assets,plugins,middleware}/**,
          web-nuxt/app.vue, web-nuxt/error.vue, web-nuxt/public/** (trừ public/data/)
KHÔNG ĐƯỢC sửa: web-nuxt/nuxt.config.ts, web-nuxt/package.json (KHÔNG thêm dependency),
                agent/**, scripts/**, web/data.json,
                CLAUDE.md, .env.example, docker-compose.yml, .gitignore

## Quy tắc
- Dùng CSS variables từ variables.css — KHÔNG hardcode màu/spacing
- KHÔNG Tailwind/UI library — giữ CSS thuần + tokens
- Giữ a11y hiện có (aria-label, role, focus-trap, touch target 44px)

## Commit: Branch session-fe, format [FE] <mô tả>. KHÔNG push/merge.

## Tasks (làm ĐÚNG THỨ TỰ — KHÔNG tự thêm)
{{5-10 TASKS}}
SAU KHI XONG: DỪNG.

## Verify mỗi commit: cd web-nuxt && npm run build

## Dừng khi: xong tasks / build fail 2 lần / cần file ngoài phạm vi
```

### Session BE template

```
## Phạm vi file (TUYỆT ĐỐI)

ĐƯỢC sửa: agent/*.py, agent/tests/**, agent/migrations/** (additive only),
          agent/data/eval/**, agent/prompts/**, requirements.txt
KHÔNG ĐƯỢC sửa: web-nuxt/**, scripts/**, web/data.json,
                CLAUDE.md, .env.example, docker-compose.yml, .gitignore

## Env vars HIỆN CÓ trên VPS prod
{{PASTE OUTPUT CỦA: ssh ... "grep -E '^[A-Z]' .env | cut -d= -f1 | sort -u"}}
KHÔNG thêm required check cho biến NGOÀI danh sách này.
Biến mới: default an toàn, ghi .env.example, note "DEPLOY NOTE: cần thêm XYZ"

## Quy tắc
- B1: backup trước thao tác dữ liệu
- B3/B4: test TRƯỚC refactor, schema change = test
- B5: mỗi commit pytest xanh
- UGC/auth = Postgres-only. SQLite endpoint UGC → 503.

## Commit: Branch session-be, format [BE] <mô tả>. KHÔNG push/merge.

## Tasks (làm ĐÚNG THỨ TỰ — KHÔNG tự thêm)
{{5-10 TASKS}}
SAU KHI XONG: DỪNG.

## Verify mỗi commit: python -m pytest -q

## Dừng khi: xong tasks / test fail 2 lần / cần file ngoài phạm vi
```

### Session Content template

```
## Phạm vi file (TUYỆT ĐỐI)

ĐƯỢC sửa: scripts/*.py (trừ deploy.sh), tests/test_*.py,
          web/data.json, web/data.js,
          web-nuxt/public/data/**, docs/** (reports, guides)
KHÔNG ĐƯỢC sửa: agent/**, web-nuxt/{components,pages,composables}/**,
                CLAUDE.md, .env.example, docker-compose.yml, .gitignore

## Quy tắc
- B1: python scripts/backup_data.py TRƯỚC MỌI thao tác dữ liệu
- B6: không re-host nội dung có bản quyền
- Ảnh: CHỈ AI-generated (cx/gpt-5.5-image) — KHÔNG stock/UGC/Wikimedia

## Commit: Branch session-content, format [Content] <mô tả>. KHÔNG push/merge.

## Tasks (làm ĐÚNG THỨ TỰ — KHÔNG tự thêm)
{{5-10 TASKS}}
SAU KHI XONG: DỪNG.

## Verify: python scripts/validate_data.py && python -m pytest tests/ -q

## Dừng khi: xong tasks / validate fail 2 lần / cần agent/ hoặc web-nuxt/ code
```

---

## Appendix B: Checklists

### Trước giao task

- [ ] Lấy env vars prod mới nhất (cho session-BE)
- [ ] Viết API contract chung (cho session-FE + BE)
- [ ] Tạo branches: `git checkout -b session-fe`, `session-be`, `session-content`
- [ ] Mỗi prompt có đủ 7 section
- [ ] Tasks <= 10, có thứ tự, có verify
- [ ] Không có chỉ dẫn ghi đè CLAUDE.md

### Merge

- [ ] `python scripts/pre_merge_check.py session-fe session-be session-content`
- [ ] Fix mọi CRITICAL
- [ ] `git merge session-be --no-edit`
- [ ] `git merge session-fe --no-edit` (resolve CLAUDE.md nếu conflict)
- [ ] `git merge session-content --no-edit`
- [ ] Restore CLAUDE.md gốc
- [ ] `python -m pytest -q` — xanh
- [ ] `cd web-nuxt && npm run build` — pass
- [ ] Deploy: `bash scripts/deploy.sh --all --skip-build`
- [ ] Verify prod: home=200, agent_health=200

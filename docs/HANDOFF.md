# BÀN GIAO DỰ ÁN vinhlong360 — Prompt tiếp quản cho Claude Code

> Dán toàn bộ file này làm tin nhắn đầu tiên cho phiên/tài-khoản Claude Code mới.
> Cập nhật lần cuối: 2026-06-24. Branch: `main`. Prod: https://vinhlong360.vn (healthy).

Bạn đang tiếp quản dự án **vinhlong360**. Hãy đọc kỹ phần dưới TRƯỚC khi làm gì.

---

## 0. Việc đầu tiên BẮT BUỘC

1. Đọc `CLAUDE.md` (hiến pháp thực thi — bất biến + giao thức, OVERRIDE mọi mặc định).
2. Đọc `docs/ROADMAP.md` (nguồn sự-thật của việc cần làm + **mục "Backlog phát sinh" ở cuối** = việc tồn đọng mới nhất).
3. Lướt `docs/architecture-decisions.md`, `docs/kien-truc-va-lo-trinh.md`, `docs/deploy-guide.md`, `docs/incident-runbook.md`, `docs/ugc-postgres.md`.
4. Chạy `python -m pytest -q` để biết baseline test (subset live-path) xanh trước khi sửa.

> ⚠️ Memory của tài-khoản cũ KHÔNG đi theo bạn. Mọi tri-thức vận-hành quan-trọng đã được chép vào file này + các docs in-repo. Tin docs in-repo; verify code hiện tại trước khi khẳng định.

---

## 1. Dự án 1 phút

MXH du lịch / OCOP / cộng đồng cho **tỉnh Vĩnh Long mới** (sáp nhập Vĩnh Long + Bến Tre + Trà Vinh).
- **Backend:** FastAPI ở `agent/` (chính: `server.py`, `public_api.py`, `social.py`, `database.py`, `notifications.py`, `auth*.py`, `storage.py`).
- **Frontend:** Nuxt 4 SSR ở `web-nuxt/` (CSS thuần + tokens, **KHÔNG Tailwind**).
- Solo dev, vibe-code, <10k user, **ngân sách <1tr đ/tháng**, web-first, **không tính-năng nặng**.
- **CHỈ GIỚI THIỆU** — không đặt hàng/booking/thanh-toán on-site (giữ tầng-nhẹ pháp-lý NĐ52/85). CTA chỉ Zalo/điện-thoại/hỏi-giá.
- Tầng nhẹ NĐ147 (mạng xã hội). Crawler chỉ trích-đoạn + link, KHÔNG re-host nội-dung/ảnh bản-quyền.

## 2. BẤT BIẾN — vi phạm = dừng (xem CLAUDE.md §2 đầy đủ)

- **B1.** Backup trước MỌI thao-tác data: `python scripts/backup_data.py`. `web/data.json` + DB **không tái-tạo được**.
- **B2.** Additive-first (thêm đường mới + verify rồi mới xoá cũ).
- **B3/B4.** Test trước khi refactor vùng-mù; một thay-đổi schema = một test.
- **B5.** Mỗi task để hệ-thống chạy được; commit nhỏ (`<GĐx.y> mô-tả`), không big-bang.
- **B6.** Không re-host ảnh/nội-dung bản-quyền (gov/báo/mytour). Ảnh chỉ nguồn cấp-phép (Wikimedia/Pexels/Unsplash) hoặc UGC.
- **B7.** KHÔNG chạy lệnh phá data (`database.py --replace`, `/admin/data-quality/apply`, `/reload`) khi chưa tới task cho-phép + chưa backup.
- **B8.** Tôn-trọng ngân-sách; không thêm dịch-vụ trả-phí. Vòng-lặp LLM nền OFF mặc-định (opt-in + cap/ngày + kill-switch).

## 3. ĐIỀU KIỆN DỪNG — phải HỎI người, không tự quyết (CLAUDE.md §4)

- Pháp-nhân/luật-sư/NĐ147/hồ-sơ pháp-lý.
- **`git push` / tạo remote** (cần URL người cấp); **đặt/rotate secret thật**; **đụng prod `.env`**.
- **Xoá file/thư-mục/data** không do roadmap chỉ-định rõ.
- **Thêm dịch-vụ trả-phí** / mua domain / bật tier trả-phí / **deploy công-khai mới**.
- Tiêu-chí nghiệm-thu không đạt sau 2 lần thử, hoặc mâu-thuẫn bất-biến §2.

## 4. Môi trường

- Windows + **PowerShell** (primary) **và Git Bash** (cho `scripts/deploy.sh`, lệnh POSIX). Mỗi cái cú-pháp riêng.
- Lệnh hay dùng:
  ```
  python -m pytest -q                 # test
  python scripts/validate_data.py     # kiểm data (phải exit 0)
  python scripts/backup_data.py       # BẮT BUỘC trước thao-tác data
  python scripts/normalize_data.py --no-backup   # sync data.json → SQLite + data.js
  cd web-nuxt; npm run build          # build FE
  ```

## 5. DEPLOY — đọc kỹ (nhiều gotcha đã trả giá)

**VPS:** Vultr `66.42.57.202`, SSH key `~/.ssh/vinhlong_vps`. Services systemd: `vl-agent` (FastAPI :8360), `vl-nuxt` (Nuxt SSR :3000), `vl-bot` (:8361), `postgres`, `nginx` (443). Live Nuxt output = `/opt/vinhlong360/web-nuxt/.output`. Prod dùng **Postgres** (UGC + entity). KHÔNG có git trên VPS (deploy bằng tarball).

**Script:** `scripts/deploy.sh` (chạy từ repo-root trong **Git Bash**):
- `--frontend [--skip-build]` · `--backend` · `--data` · `--replace` (re-import data.json vào prod PG, DESTRUCTIVE) · `--no-backup` (nguy-hiểm).
- Tự: pre-flight health → (build) → backup prod (db dump + code tar) → scp → `rm -rf .output` + extract → npm/pip → restart → verify (home 200 + agent_health 200).

**QUY TRÌNH FE chuẩn (tránh timeout giết build → ship .output rỗng → 502):**
```
cd web-nuxt && rm -rf .output .nuxt && NODE_OPTIONS="--max-old-space-size=4096" npm run build   # chạy NỀN (background)
# đợi build xong, KIỂM .output/server/index.mjs tồn-tại + grep marker thay-đổi trong .output/public/_nuxt/*.css
cd .. && bash scripts/deploy.sh --frontend --skip-build
```
- **KHÔNG** chạy `deploy.sh` có build-inside ở foreground Bash (timeout 120s cắt giữa build).
- Trên Windows: `rm -rf .output` đơn-lẻ có-thể để sót chunk cũ → **luôn `rm -rf .output .nuxt`** (chunk lệch = ERR_MODULE_NOT_FOUND).
- Build prod: nếu có `web-nuxt/.env` chứa `API_BASE` → bị bake vào routeRules → 502. **Xoá `.env` trước khi build.**
- LUÔN verify: `home=200` và `agent_health=200` (agent_health = curl `/api/homepage` qua nginx). Bất kỳ deploy đụng startup/DB-load của agent PHẢI verify `:8360/health`, không chỉ home.
- **Migrations KHÔNG được deploy.sh ship** → áp tay: `ssh -i ~/.ssh/vinhlong_vps root@66.42.57.202 "sudo -u postgres psql -d vinhlong360 -f -"`; bảng MỚI cần `ALTER TABLE x OWNER TO vl360`.
- **Đĩa VPS 23GB**: backup pre-deploy ~150MB/lần. deploy.sh đã thêm **xoay-vòng giữ 6 bản**. Nếu "build+deploy mà prod vẫn bản cũ" → `ssh ... 'df -h /'` (từng đầy 100% → deploy ship nhầm .output cũ) + so CSS hash deployed vs local.

## 6. ⚠️ GOTCHA QUAN TRỌNG NHẤT — SSR fetch

**Internal `$fetch('/api/...')` trong `useAsyncData` (SSR render) BỊ LỖI** (Nitro proxy nội-bộ 502/"fetch failed" khi render route) → useAsyncData rỗng → payload thiếu key → client tin payload, KHÔNG refetch → **trang RỖNG entity (silent)**. Đã từng làm ~18 trang catalog/list rỗng mà không ai biết.

**LUẬT:** mọi page/component SSR-fetch `/api/**` PHẢI dùng `web-nuxt/utils/apiFetch.ts` (auto-import), **KHÔNG** `$fetch` trực-tiếp:
```ts
const { data } = await useAsyncData('key', () => apiFetch('/api/...'))
```
`apiFetch` = server fetch qua origin công-khai `https://vinhlong360.vn` (đi nginx→backend ổn-định), client dùng relative. `$fetch` trực-tiếp CHỈ OK cho lệnh **client** (event handler, onMounted, POST action, `{server:false}`). Verify SSR bằng `curl https://vinhlong360.vn/<route> | grep -c '/dia-diem/'` (đếm link entity) — KHÔNG chỉ check HTTP 200.

## 7. Data flow (DB là nguồn sự-thật)

- `web/data.json` = nguồn entity/relationship/itinerary (export + build prerender). Sửa data: **data.json → `backup_data.py` → `validate_data.py` (exit 0) → `deploy.sh --replace` (đẩy prod) → `normalize_data.py` (sync data.js + SQLite local)**.
- **UGC/auth (users/posts/comments/follow/...) = Postgres-only.** Dev cộng-đồng: `docker compose up postgres`. Endpoint UGC trên SQLite trả 503 cố-ý. KHÔNG port UGC sang SQLite.
- `--replace` cần `ALLOW_DESTRUCTIVE_DB_REPLACE=1` (deploy.sh tự set khi `--replace`) + restart vl-agent để reload RAM cache.
- **Số xã/phường ĐÚNG = 124** (89 xã + 35 phường). `/api/places` = 125 (124 + 1 tỉnh). Thống-kê "Xã phường" đếm `level IN (xa,phuong)`.

## 8. Secrets / an-toàn (KHÔNG đụng)

- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` (Cloudflare R2, ảnh) + prod `.env` do **CHỦ đặt** — Claude KHÔNG handle/đặt giá-trị thật, KHÔNG sửa prod `.env` (parse-error = crash-loop vl-agent vì `server.py` hard-read `os.environ["LLM_API_KEY"]`).
- Duyệt ảnh ở `/admin/duyệt-ảnh` là **cổng người** — Claude có-thể TỪ-CHỐI ảnh không hợp-lệ nhưng KHÔNG tự duyệt.
- Tham-chiếu LLM/Image API: dùng nội-bộ (ChatGPT-compatible) — xem code `agent/` + scripts `gen_image.py`. KHÔNG thêm provider trả-phí.

## 9. Trạng thái HIỆN TẠI (2026-06-24, đã deploy + verify prod)

**Trang chủ (index.vue) — đã hoàn-thiện:** hero ảnh-thật + Ken-Burns + **bất-đối-xứng** (chữ trái + thẻ featured phải ≥920px) · stats count-up + stat-strip · featured-event "đang diễn ra" + sheen · 2 bento (3-vùng, sở-thích) · **Spotlight** magazine · **2 interstitial** "act-break" (Ba dòng sông / Kể câu chuyện) · band xen-kẽ · placeholder EntityCard mã-màu theo loại · content-visibility · scroll-margin WCAG 2.2 · View-Transitions · Speculation-Rules · dark-mode chuẩn (`color-scheme` + token). Mọi animation composited + **tự tắt khi prefers-reduced-motion** (a11y).

**Trang catalog:** `du-lich`/`san-pham` có `CatalogSpotlight` (component dùng-chung) + catalog-hero editorial (h1 lớn + stat divider, shared catalog.css).

**Bug-hunt 2026-06-24 (đa-agent + runtime) — đã fix + verify:**
1. ~18+9 trang SSR-fetch rỗng → `apiFetch` (xem §6).
2. `/api/feed?area=` rỗng (social.py dùng sai cột) → đã sửa.
3. `/api/entities?q=` bỏ offset → search lặp → `search_entities` thêm offset + `ORDER BY confidence, id`.
4. "Xã phường" 162→**124** (get_stats đếm level xa/phuong; danh-ba bỏ 'tinh').
5. Reclass **37 entity** gán-nhầm `type=place` (ngân-hàng/quán/bệnh-viện/bến-xe/chùa) → 12 dish, 24 facility (office_kind y_te/buu_dien/cong_an/khac), 1 attraction. `/api/places` sạch.
6. Hardening: follow guard entity tồn-tại.
- SẠCH (đã quét): FE data-shape/route/logic/hydration · BE auth/SQL-injection/upload/503 · runtime 0 lỗi console.

## 10. BACKLOG ưu-tiên (chi-tiết ở cuối docs/ROADMAP.md "Backlog phát sinh")

- **[SEO] `/sitemap-media.xml` + child sitemap 404** — backend `seo.py` có route nhưng **nginx chưa proxy** → cần thêm route nginx (cần truy-cập server config / chủ duyệt §4).
- **[Nội-dung, giá-trị cao] ~372 mô-tả entity mỏng (<120 ký-tự)** — viết lại chuẩn giọng + có nguồn (dùng skill `viet-content-optimizer` nếu có; nếu không, theo `docs` + anti-hallucination: KHÔNG bịa fact HC/địa-chỉ). 12 nhà-hàng vừa reclass→dish cũng chỉ có địa-chỉ/giờ, cần mô-tả.
- **[Ảnh] đa-số entity chưa có ảnh** (đang placeholder mã-màu) — chờ chủ duyệt ảnh ở `/admin/duyệt-ảnh`; rồi mới bật spotlight-ảnh-lớn + AVIF.
- **[Low] report-ugc/block guard target · site-settings plugin→apiFetch.**
- **Nhân bố-cục** (bento/band/spotlight) sang các trang catalog còn lại (lễ-hội/lưu-trú/ocop/theo-mùa).

## 11. Verify trực-quan (mẹo)

- Build prod local rồi xem qua preview MCP (`nuxt-prod` trong `.claude/launch.json` = `node web-nuxt/.output/server/index.mjs`) — **preset mobile (375) đo được**, desktop preset có-thể = 0px (headless) → đo desktop qua trình-duyệt thật trỏ prod.
- Screenshot prod: nếu thấy "wash trắng" toàn trang nhưng DOM/eval báo tối đúng → **glitch công-cụ chụp**, KHÔNG phải lỗi site (tin computed-style/eval hơn ảnh). Test-profile có-thể bật reduce-motion → animation tắt khi quan-sát (đúng, không phải bug); production user thường thấy đầy-đủ.
- `content-visibility:auto` khiến element off-screen trả `width 0` khi eval → `scrollIntoView` trước khi đo.

---

## 12. Bàn-giao CREDENTIAL — CHỦ tự làm, KHÔNG qua AI/không commit

> ⚠️ Claude KHÔNG thu-thập/hiển-thị/truyền/commit secret thật, KHÔNG đọc prod `.env`. Mục này chỉ là **checklist loại credential + cách bàn-giao an-toàn**. Mọi giá-trị do CHỦ truyền trực-tiếp cho người tiếp-quản qua kênh bảo-mật (password-manager dùng-chung / age/gpg / Signal) — KHÔNG qua git, chat, email-plaintext, hay AI. Repo đã verify sạch secret (`.env` gitignored; chỉ dummy CI).

**Cần bàn-giao (giá-trị KHÔNG ở đây):**
1. **VPS SSH** — key riêng `~/.ssh/vinhlong_vps` → `root@66.42.57.202` (Vultr). *Khuyến-nghị:* người mới tự tạo keypair, gửi **public key** cho chủ, chủ thêm vào `/root/.ssh/authorized_keys` (không phải copy private key cũ → revoke được). Có SSH là đọc được prod `.env` tại `/opt/vinhlong360/.env` (không cần truyền .env riêng).
2. **Vultr** (provider VPS) — login chủ.
3. **Tên miền `vinhlong360.vn`** — tài-khoản registrar + DNS.
4. **Cloudflare** — account (bucket R2 `vinhlong360`, CDN `cdn.vinhlong360.vn`). Secret: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
5. **Prod `.env`** (`/opt/vinhlong360/.env`, đã có sẵn trên VPS) — gồm các key (TÊN): `DATABASE_URL` (mật-khẩu Postgres user `vl360`), `LLM_API_KEY`+`LLM_BASE_URL`+`LLM_MODEL` (LLM provider ChatGPT-compatible), `IMAGE_API_KEY` (gen ảnh), `R2_*`, `ADMIN_API_KEY` (đăng-nhập /admin), `ESMS_API_KEY`/`ESMS_SECRET`/`ESMS_BRANDNAME` (OTP SMS — eSMS.vn), `ZALO_OA_ID`/`ZALO_OA_SECRET` (bot Zalo, nếu dùng), `MEMORY_ENCRYPTION_KEY`, `CORS_ORIGINS`, `ENVIRONMENT=production`.
6. **Provider accounts** sau LLM/Image API, **eSMS.vn** (OTP), **Zalo OA** — login chủ (để rotate/billing).
7. **Git remote**: HIỆN không có remote (deploy bằng tarball). Nếu muốn push GitHub → chủ tạo repo + cấp URL/quyền (Claude không tự push — §4).

**Khi muốn CẮT quyền tài-khoản/người cũ (rotate):** chủ tự làm — gỡ SSH key cũ khỏi `authorized_keys`; xoay `R2` keys (Cloudflare), `ADMIN_API_KEY`, mật-khẩu Postgres (cập-nhật `DATABASE_URL`), `LLM_API_KEY`, `ESMS`/`ZALO` secret; sửa prod `.env` rồi `systemctl restart vl-agent`. **Lưu-ý:** sai cú-pháp `.env` = crash-loop vl-agent (xem incident-runbook) → backup `.env` trước khi sửa.

---

**Tóm tắt 1 câu:** Đọc CLAUDE.md + ROADMAP, theo bất-biến §2 + điều-kiện-dừng §4, deploy qua `scripts/deploy.sh` (build FE tách-nền + verify 200), **dùng `apiFetch` cho mọi SSR-fetch**, backup trước mọi data-op, KHÔNG đụng secret/prod-.env/git-push khi chưa được chủ duyệt.

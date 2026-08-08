> STATUS: active — bản đồ nhánh & worktree. Chụp 2026-08-07, **hợp nhất về `main` ngày 2026-08-08**.
> Mâu thuẫn với `CLAUDE.md` → CLAUDE.md thắng.

# Bản đồ nhánh & worktree — vinhlong360

## 0. Trả lời trong 30 giây

| Câu hỏi | Trả lời |
|---|---|
| **Trunk thật nằm ở đâu?** | **`main`.** Không còn nhánh phát triển song song. |
| **Tôi nên checkout gì để làm tiếp?** | `main`. Clone về là dùng được ngay. |
| **Có gì đang treo/mất được không?** | **Không.** 102 commit từng chỉ có ở local đã được push ngày 2026-08-08; `git rev-list` đếm 0 commit ngoài origin. |

## 0b. Chuyện gì đã xảy ra ngày 2026-08-08

Trước hôm đó: 22 nhánh, 20 worktree, `main` thiếu **246 commit** so với trunk thật
(`codex/tri-region-color`), và **98 commit chưa bao giờ rời khỏi máy**. Người clone repo
về nhận `origin/main` bản 11-07 — thiếu 847 commit — mà không chỗ nào nói trunk ở đâu.

Đã xử lý theo thứ tự chi phí đo được (`git merge-tree`, không đụng cây làm việc):

| Nhánh | Xung đột | Kết quả |
|---|---|---|
| `codex/tri-region-color` | 0 (main là tổ tiên) | fast-forward |
| `codex/phase4-multiday-allocation` | 0 | hợp sạch |
| `codex/non-public-wave0` | 1 file | hợp |
| `fix/truthful-public-claims` | 1 file | hợp |
| `t7/crawler-pinned` + `claude/competent-northcutt-622292` | 4 + 3 file | **không hợp** — trùng nhau và trunk đã có bản tương đương; port đúng 1 ca kiểm còn hở rồi bỏ nhánh |
| `codex/np1-identity-location-trust` | 15 file + đụng số migration | hợp, đánh số lại 071/072/073 → **076/077/078** |

Ba cái giá phải trả, ghi lại để không ai tưởng là miễn phí:

1. **Baseline complexity 17 → 23.** `phase4` phát triển ngoài tầm cổng nên mang theo 6 hàm
   vượt ngưỡng. Nâng trần theo §3.7 kèm giải trình thay vì refactor thuật toán DP giữa lúc
   merge. **Nợ chưa đóng** — xem Backlog phát sinh trong `docs/ROADMAP.md`.
2. **`PG_REQUIRED_SCHEMA_VERSION` 74 → 78.** Code NP-1 đọc `user_preferences`/`consents`/
   `events` nên thật sự cần cả ba migration mới đã chạy. **Migration 076-078 CHƯA CHẠY ở
   đâu cả** — prod vẫn ở mức cũ.
3. **Hai thiết kế trùng vai được giữ cả hai, gate bằng cờ.** `EntityTrustPanel` (main) và
   `SourceTrustDrawer` + thẻ "Độ tin cậy dữ liệu" (NP-1) cùng nói về độ tin cậy nguồn;
   `v-if="!trustVisible"` đảm bảo chỉ một cái hiện, cờ `trust_drawer_v1` quyết cái nào.
   Tương tự với `SmartRecommendations` (lý do tĩnh vs nút mở drawer).

Bốn chỗ vẫn còn sai sự thật trên sản phẩm sau khi hợp — xem §3.4, trong đó
`web-nuxt/pages/dia-diem/[id].vue:1239` vẫn bịa `ratingCount: '1'`.

---

## 1. Hình dạng thật của lịch sử

Sai lầm dễ mắc nhất là đo mọi thứ **so với `main`**. Đo như vậy ra 11 nhánh "còn việc riêng".
Đo so với **trunk thật** (`codex/tri-region-color`) thì chỉ còn **6**.

```
origin/main (1b9f2bd9, 11-07)
    └── … 601 commit chưa push …
        └── main (aebf4afe, 04-08)   ← tổ tiên của trunk, KHÔNG có gì riêng
            └── … 246 commit …
                └── codex/tri-region-color (10d9bb69, 07-08)   ← TRUNK
                    (origin/codex/tri-region-color = 24e093b8, còn thiếu 16 commit cuối)
```

`main` nằm **bên trong** trunk (`git rev-list --left-right --count main...codex/tri-region-color` = `0 246`).
Vì vậy: **không có việc gì trên `main` mà trunk chưa có.** Trunk là bản duy nhất cần quan tâm.

---

## 2. Rủi ro mất việc — phần quan trọng nhất của tài liệu này

Repo `origin` = `https://github.com/nctaam/vinhlong360.git`. Trên đó **chỉ có 2 nhánh**:

| Ref trên GitHub | Commit | Ngày |
|---|---|---|
| `origin/main` | `1b9f2bd9` | 2026-07-11 |
| `origin/codex/tri-region-color` | `24e093b8` | 2026-08-07 |

**20/22 nhánh local chưa bao giờ được push.**

Tin tốt: phần lớn nội dung của chúng đã nằm trong `origin/codex/tri-region-color` (vì đã hợp vào trunk và trunk đã push). Kể cả tip của `main` cũng nằm trong đó — kiểm bằng `git merge-base --is-ancestor main origin/codex/tri-region-color` → true.

Tin xấu: **98 commit không nằm trong bất kỳ ref nào của origin.** Máy hỏng = mất thật.

```
git rev-list --count $(git for-each-ref --format='%(refname:short)' refs/heads/ | tr '\n' ' ') \
    ^origin/main ^origin/codex/tri-region-color
# → 98
```

98 commit đó chia ra:

| Nhánh | Commit local-only | Nội dung | Mức thiệt hại nếu mất |
|---|---:|---|---|
| `codex/np1-identity-location-trust` | 63 | ~21.400 dòng: toàn bộ hệ preference/consent vị trí + cá nhân hoá + trust drawer | **Rất nặng** — 3 ngày làm việc dày, không tái tạo được |
| `codex/tri-region-color` (16 cuối) | 16 | lịch vạn niên, thời tiết trang chủ, ẩn/bỏ ẩn bài, migration 075, sửa iCal, atomic write | **Nặng** — công việc mới nhất |
| `codex/phase4-multiday-allocation` | 12 | ~3.100 dòng: phân bổ lịch trình nhiều ngày (DP) | Nặng |
| `codex/non-public-wave0` | 4 | ~2.200 dòng: RBAC scope cho AdminCP + trang 403 | Trung bình |
| `fix/truthful-public-claims` | 1 | gỡ 6 claim sai sự thật (xem §3.4 — **vẫn chưa vào trunk**) | Trung bình, nhưng là lỗi đang chạy |
| `t7/crawler-pinned` | 1 | pin egress crawler | Thấp — trunk đã có bản tương đương |
| `claude/competent-northcutt-622292` | 1 | pin egress crawler (bản song song) | Thấp — trùng t7 |

**Kiến nghị (chủ dự án quyết):** push 4 nhánh đầu lên origin trước khi làm bất cứ việc dọn dẹp nào. Push là thao tác cần chủ dự án theo CLAUDE.md §4 — tài liệu này không tự làm.

---

## 3. Sáu nhánh còn việc riêng so với trunk

Đo bằng `git rev-list --left-right --count codex/tri-region-color...<nhánh>`.

### 3.1 `codex/np1-identity-location-trust` — 63 commit riêng (2026-07-28 → 07-30)

**Chứa gì.** NP-1 "identity / location / trust": hợp đồng preference vị trí của người dùng + consent, API preference/consent, ranh giới phân giải vị trí tạm thời (không lộ toạ độ), lưu event cá nhân hoá có giới hạn + purge riêng tư, tầng nguồn & độ tươi cho tín hiệu cá nhân hoá, drawer "Vì sao thấy cái này" + "Nguồn & mức tin cậy", flow onboarding preference thích ứng, và một vòng NP-1.1 sửa lỗi vị trí (self-healing, chống race khi xác nhận, reconfirm recovery).

File mới đáng kể: `agent/user_preferences.py` (1084 dòng), `web-nuxt/composables/usePersonalizationPreferences.ts`, `web-nuxt/components/PersonalizeSetupSheet.vue` / `WhyThisDrawer.vue` / `SourceTrustDrawer.vue`, `web-nuxt/types/personalization.ts`, ~3.000 dòng test frontend.

**Trunk đã có chưa.** **Chưa.** Không file nào trong số trên tồn tại trên trunk (`git ls-tree -r --name-only codex/tri-region-color | grep user_preferences` → rỗng). Chữ "personalization" trên trunk chỉ xuất hiện ở `agent/memory.py`/`proactive.py` — code cũ, khác việc.

**Còn giá trị không.** Có. Không có tính năng nào của nó bị trunk làm lại theo cách khác.

**Cản trở khi hợp — có thật, đã đo:**
- **Đụng số migration.** Nhánh này định nghĩa `071_identity_location_preferences.sql`, `072_personalization_legacy_purge_queue.sql`, `073_location_preference_remediation.sql`. Trunk **cũng có** 071/072/073 với nội dung hoàn toàn khác (`071_restore_entity_rating_triggers`, `072_feedback_receipts`, `073_account_erasure_state`) và đã đi tới 075. Hợp vào **bắt buộc đánh số lại thành 076/077/078** và kiểm lại `check_migration_gate`.
- 19/58 file nó chạm cũng bị trunk sửa từ lúc rẽ nhánh — gồm `agent/auth.py`, `agent/database.py`, `agent/public_api.py`, `web-nuxt/pages/cai-dat.vue`, `web-nuxt/pages/dia-diem/[id].vue`.

Điểm rẽ: `42edfdbb` (2026-07-28). Worktree: `C:\Code\vl360-wt\np1-identity-location-trust` (sạch).

### 3.2 `codex/phase4-multiday-allocation` — 12 commit riêng (2026-07-30)

**Chứa gì.** Phase 4 của "zero-cost itinerary intelligence": hợp đồng phân bổ nhiều ngày, endpoint DP, cân bằng tải giữa các ngày, tích hợp vào bộ sinh lịch trình, deadline chung cho scheduler nhiều ngày. File mới `agent/itinerary_multiday.py` (992 dòng) + 573 dòng test + spec/plan trong `docs/superpowers/`.

**Trunk đã có chưa.** **Chưa** — `git grep -l -i multiday codex/tri-region-color -- agent` → rỗng. Lưu ý: nhánh này đứng trước `main` 58 commit nhưng **46 trong đó đã vào trunk rồi** (Phase 1–3 của cùng roadmap). Chỉ 12 commit Phase 4 là còn riêng.

**Còn giá trị không.** Có, và đây là nhánh **rẻ nhất để hợp**: chỉ 2/8 file chạm bị trunk đụng (`agent/itinerary_gen.py`, `docs/api-contract.md`).

Điểm rẽ: `30ecaf06` (2026-07-30). Worktree: `C:\Code\vinhlong360\.worktrees\phase4-multiday-allocation` (sạch).

### 3.3 `codex/non-public-wave0` — 7 commit riêng (4 thật sự riêng)

**Chứa gì.** Wave 0 của khu vực non-public: hợp đồng admin scope dùng chung, resolver quyền truy cập AdminCP theo scope, panel trạng thái hệ thống dùng lại được + trang `403.vue`, thu hẹp shell AdminCP và command palette theo scope. File mới: `agent/admin_permissions.py`, `web-nuxt/utils/adminAccess.ts`, `web-nuxt/components/system/SystemStatePanel.vue`, `web-nuxt/pages/403.vue`.

3 commit đầu (`8f2d913e`, `b0f29bcb`, `890f06a0`) là **doc dùng chung với `codex/np1-identity-location-trust`** — nếu hợp np1 trước thì phần này tự biến mất.

**Trunk đã có chưa.** **Chưa** — `git grep -l "admin_permissions\|adminAccess\|AdminScope"` trên trunk → rỗng.

**Còn giá trị không.** Có. Chỉ 4/18 file chạm bị trunk đụng (`agent/admin.py`, `agent/auth.py`, `web-nuxt/types/index.ts`, `web-nuxt/tests/ui-foundation-shell.test.ts`).

Lưu ý bối cảnh: spec/plan liên quan (`docs/superpowers/plans/2026-07-28-non-public-wave0-rbac-state-foundation.md` và file `-design.md` tương ứng) hiện đang **untracked ở repo gốc** `C:\Code\vinhlong360` — chưa commit ở đâu cả.

Điểm rẽ: `42edfdbb` (2026-07-28). Worktree: `C:\Code\vl360-wt\non-public-wave0` (untracked `.superpowers/`).

### 3.4 `fix/truthful-public-claims` — 1 commit (`ae959c40`, 2026-07-27) — **CÒN GIÁ TRỊ, ĐANG LÀ LỖI SỐNG**

**Chứa gì.** Gỡ 6 khẳng định mà dữ liệu không đỡ được, mỗi cái đều có số đo kèm trong commit message.

**Trunk đã có chưa.** **Chưa.** Đã kiểm từng chỗ trên `codex/tri-region-color`:

| Chỗ | Tình trạng trên trunk |
|---|---|
| `agent/seo.py` `_jsonld_rating_fallback` | **Vẫn còn** (dòng 832). Vẫn phát `aggregateRating` lấy từ `attrs.rating` — dữ liệu sao của bên thứ ba (125/126 mục ghi nguồn `foody.vn`). Đây là claim sở-hữu-đánh-giá gửi thẳng cho máy tìm kiếm → chạm **CLAUDE.md §1.7** và **§B6**. |
| `web-nuxt/pages/lien-he.vue` dòng 11 | **Vẫn còn** "hai người đọc từng tin nhắn" — dự án có 1 người |
| `web-nuxt/pages/gioi-thieu.vue` dòng 62 | **Vẫn còn** "hai người đọc từng tin nhắn" |
| `web-nuxt/pages/huong-dan.vue` dòng 461 | **Vẫn còn** "9.500 mối quan hệ … Vĩnh Long, Bến Tre, Trà Vinh" — sai số (thật ~12.060) **và** trình bày 3 tỉnh như đang tồn tại → chạm **§1.6** |
| Mục FAQ ảnh trong `huong-dan.vue` liệt kê các nguồn ảnh mà §1.5 đã cấm | **Đã được sửa ở nơi khác** trên trunk — phần này của nhánh đã lỗi thời |
| `web-nuxt/pages/dia-diem/[id].vue` dòng 1239-1245 | **Vẫn còn** — phát `ld.aggregateRating` từ `e.attributes.rating` và **bịa `ratingCount: '1'`** khi không có số lượng thật. Cùng lớp vi phạm §1.7/§B6 với `seo.py`, cùng đường ra máy tìm kiếm |

**Kiến nghị:** đây là nhánh nên xử lý sớm nhất bất kể quyết định merge lớn thế nào — nội dung 1 commit, hầu hết vẫn áp dụng được, và trunk đang chạy với 5 chỗ sai. Site đang noindex (`NUXT_PUBLIC_SITE_NOINDEX`) nên chưa mất thứ hạng, đúng như commit message nói.

Worktree: `C:\Code\vl360-wt\content` (sạch).

### 3.5 `t7/crawler-pinned` — 1 commit (`9712edbb`) — **đã bị thay thế**

Pin egress crawler + vá authority escape (`agent/crawler.py`, `tests/test_crawler_ssrf.py`).

`git cherry` báo "chưa có upstream" **nhưng đó là sai lệch do rebase/viết lại**. Trunk đã có bản tương đương và tốt hơn: `agent/crawler.py` trên trunk dùng `_resolve_crawl_target` + `_PINNED_HTTP` với `EgressPolicy`, và `tests/test_crawler_ssrf.py` trên trunk phủ 7 ca (userinfo escape `@evil.tld/x`, `//evil.tld/x`, `https://evil.tld/x`, `//user@vinhlongtourist.vn/x`, `file:///etc/passwd`, chặn redirect ra ngoài trước khi dial, theo redirect same-origin) **cộng thêm** một chốt mà nhánh t7 không có: fixture ném `AssertionError` nếu crawler còn gọi `httpx.get` không pin.

**Kiến nghị:** bỏ. Không thấy ca kiểm nào của t7 mà trunk bỏ sót.

### 3.6 `claude/competent-northcutt-622292` — 1 commit (`7b33c91b`) — **trùng 3.5, đã bị thay thế**

Cùng một việc với `t7/crawler-pinned`, do một agent khác làm song song (hai bản `agent/crawler.py` lệch nhau 40 dòng). Cũng đã bị bản trên trunk thay thế. **Kiến nghị: bỏ.** Nhánh này không có worktree.

---

## 4. Mười bốn nhánh đã hợp hết — xác nhận

Kiểm bằng `git merge-base --is-ancestor <nhánh> codex/tri-region-color` → **true với cả 14**, tức không còn commit riêng nào.

| Nhánh | Là gì | Trước trunk |
|---|---|---|
| `codex/pinned-egress-observability` | quan sát egress đã pin; **đây là nhánh mà repo gốc `C:\Code\vinhlong360` đang checkout** | 0 |
| `codex/pinned-egress-observability-impl` | phần cài đặt của cùng việc trên | 0 |
| `codex/security-correctness-wave0` | vá privacy/cache, bound request Nuxt→backend, giữ auth state khi logout preflight lỗi | 0 |
| `codex/trust-erasure-closure` | đóng vòng erasure/trust, baseline backend sạch | 0 |
| `fix/egress-address-policy` | chặn site-local / IPv4-translated / 6to4-relay; đã gộp t4+t6 | 0 |
| `t4/admin-pinned` | pin fetch ảnh của admin | 0 |
| `t5/auto-learn-pinned` | pin fetch nguồn auto-learn | 0 |
| `t6/quality-burst-pinned` | pin fetch nguồn quality-burst | 0 |
| `claude/loving-sutherland-2495d6` | sửa deadlock AB-BA trong path lock của `versioned_json_store` | 0 |
| `claude/vigilant-haibt-379b3e` | bóc BOM UTF-8 làm checker bỏ sót file trong im lặng | 0 |
| `claude/pensive-dhawan-f7baae` | pinned Telegram egress + thay source guard bằng behavior test; **tip trùng đúng `main`** | 0 |
| `claude/reverent-lederberg-a15670` | CI chạy mọi nhánh, quét khả chuyển script vận hành, vá 4 test closed-installer chỉ đỏ trên Linux | 0 |
| `codex/homepage-b1-nocturne` | pilot homepage nocturne | 0 |
| `codex/zero-cost-route-optimizer` | tối ưu tuyến zero-cost + ranh giới vòng đời map | 0 |

Hai điểm cần nói rõ vì dễ hiểu sai:

- `claude/reverent-lederberg-a15670` đứng trước `main` **221 commit** nên nhìn như một nhánh song song lớn. Thực ra nó là **tổ tiên trực tiếp của trunk** — trunk đứng trước nó đúng 25 commit. Không có gì riêng.
- `codex/homepage-b1-nocturne` (67 trước main), `codex/pinned-egress-observability` (61), `codex/zero-cost-route-optimizer` (21) cũng vậy: trước `main` nhưng **nằm trọn trong trunk**.

---

## 5. Hai mươi worktree — ba thư mục khác nhau, không có quy ước nào ghi ở đâu

Người mới sẽ không đoán được là worktree nằm rải ở **ba gốc**: `C:\Code\vinhlong360\.worktrees\`, `C:\Code\vl360-wt\`, `C:\Code\worktrees\` (+ 2 cái do harness tạo trong `.claude\worktrees\`).

| Đường dẫn | Trỏ tới | Bẩn | Đánh giá |
|---|---|---|---|
| `C:\Code\vinhlong360` | `codex/pinned-egress-observability` | 8 mục | **Bẫy.** Đây là repo gốc, nhưng đang đứng trên nhánh cũ hơn trunk 278 commit. Ai mở thư mục này ra làm việc là làm trên bản cũ. |
| `C:\Code\vinhlong360\.worktrees\tri-region-color` | **`codex/tri-region-color`** | sạch | **Chỗ làm việc.** |
| `C:\Code\vl360-wt\np1-identity-location-trust` | `codex/np1-identity-location-trust` | sạch | **Giữ** — 63 commit chưa hợp |
| `C:\Code\vinhlong360\.worktrees\phase4-multiday-allocation` | `codex/phase4-multiday-allocation` | sạch | **Giữ** — 12 commit chưa hợp |
| `C:\Code\vl360-wt\non-public-wave0` | `codex/non-public-wave0` | `.superpowers/` untracked | **Giữ** — 7 commit chưa hợp |
| `C:\Code\vl360-wt\content` | `fix/truthful-public-claims` | sạch | **Giữ** — 1 commit còn giá trị (§3.4) |
| `C:\Code\vl360-wt\t7` | `t7/crawler-pinned` | sạch | Rác — nhánh đã bị thay thế |
| `C:\Code\vl360-wt\t4` | `t4/admin-pinned` | sạch | Rác — đã hợp |
| `C:\Code\vl360-wt\t5` | `t5/auto-learn-pinned` | sạch | Rác — đã hợp |
| `C:\Code\vl360-wt\t6` | `t6/quality-burst-pinned` | sạch | Rác — đã hợp |
| `C:\Code\vl360-wt\t9` | `fix/egress-address-policy` | `FIX-REPORT.md` untracked | Rác — đã hợp. **Đọc `FIX-REPORT.md` trước khi bỏ** (chưa commit ở đâu). |
| `C:\Code\vl360-wt\pinned-egress-observability` | `codex/pinned-egress-observability-impl` | sạch | Rác — đã hợp |
| `C:\Code\vl360-wt\security-correctness-wave0` | `codex/security-correctness-wave0` | sạch | Rác — đã hợp |
| `C:\Code\vl360-wt\zero-cost-route-optimizer` | `codex/zero-cost-route-optimizer` | sạch | Rác — đã hợp |
| `C:\Code\vinhlong360\.worktrees\homepage-b1-nocturne` | `codex/homepage-b1-nocturne` | sạch | Rác — đã hợp |
| `C:\Code\worktrees\vinhlong360-deep-scan-main` | `codex/trust-erasure-closure` | sạch | Rác — đã hợp. Tên thư mục nói "main" nhưng trỏ nhánh khác. |
| `C:\Code\worktrees\vinhlong360-main-merge` | `main` | sạch | Rác — `main` không có gì riêng |
| `C:\Code\vinhlong360\.worktrees\tmp-main-baseline` | detached `aebf4afe` (= `main`) | sạch | **Rác rõ ràng** — tên `tmp-*`, detached, trỏ đúng tip `main` |
| `C:\Code\vinhlong360\.claude\worktrees\pensive-dhawan-f7baae` | detached `aebf4afe` (= `main`) | sạch | Rác — do harness tạo, detached, trùng `main` |
| `C:\Code\vinhlong360\.claude\worktrees\reverent-lederberg-a15670` | `claude/reverent-lederberg-a15670` | sạch | Rác — đã hợp |

`git worktree prune --dry-run` không thấy cái nào hỏng — cả 20 thư mục đều còn tồn tại thật.

### Việc chưa commit đang nằm rải rác

| Ở đâu | Gì |
|---|---|
| `C:\Code\vinhlong360` | `M design-system/vinhlong360/pages/home.md`; untracked: `.superpowers/`, `agent/knowledge.db-shm`, `agent/knowledge.db-wal`, `design-system/vinhlong360/concepts/`, `docs/page-inventory-design-scope-2026-07-27.md`, `docs/superpowers/plans/2026-07-28-non-public-wave0-rbac-state-foundation.md`, `docs/superpowers/specs/2026-07-28-non-public-wave0-rbac-state-foundation-design.md` |
| `C:\Code\vl360-wt\t9` | untracked `FIX-REPORT.md` |
| `C:\Code\vl360-wt\non-public-wave0` | untracked `.superpowers/` |

`agent/knowledge.db-shm` / `-wal` là file phụ của SQLite — dấu hiệu DB **đang mở hoặc đóng không sạch** ở repo gốc. Hai spec/plan non-public-wave0 chỉ tồn tại ở đây, chưa commit ở nhánh nào.

---

## 6. Stash

Có đúng **1 stash**:

```
stash@{0}: On codex/tri-region-color: weather-wip
```

Tên là "weather-wip" nhưng nội dung là **lịch âm**, không phải thời tiết: `scripts/gen_lunar_fixture.py`, `web-nuxt/composables/useLunar.ts`, `web-nuxt/tests/fixtures/lunar-oracle.json` (+68.021 dòng), `lunar-oracle-parity.test.ts`, `IconLine.vue`, `pages/index.vue`. Base là `c5379506`.

**Đã được commit rồi.** So stash với tip trunk hiện tại, mọi file trùng **byte-for-byte** trừ đúng **1 dòng comment**:

```
-# Khối mở rộng (can chi / tiết khí / âm→dương). Các khối cũ ở trên KHÔNG đổi.
+# Khối mở rộng (JD / can chi / tiết khí / âm→dương). Các khối cũ ở trên KHÔNG đổi.
```

Trunk là bản **mới hơn** (có thêm chữ "JD"). Stash chính là WIP đã trở thành commit `71a8f19c` ("feat: trang lịch vạn niên"). Không còn gì để cứu.

**Kiến nghị: drop.** Nhưng đây là thao tác xoá dữ liệu → cần chủ dự án (CLAUDE.md §4). Tài liệu này không tự drop.

---

## 7. Bảng kiến nghị — **KIẾN NGHỊ, KHÔNG PHẢI QUYẾT ĐỊNH**

Chủ dự án quyết. CLAUDE.md §4 cấm tự merge / push / xoá nhánh.

### Ưu tiên 1 — chống mất việc (làm trước mọi thứ khác)

| Việc | Đối tượng | Vì sao |
|---|---|---|
| Push | `codex/tri-region-color` (16 commit cuối) | Việc mới nhất, chưa có bản sao nào |
| Push | `codex/np1-identity-location-trust` | 63 commit / 21.400 dòng chỉ có trên máy này |
| Push | `codex/phase4-multiday-allocation` | 12 commit / 3.100 dòng |
| Push | `codex/non-public-wave0` | 4 commit riêng / 2.200 dòng |
| Push | `fix/truthful-public-claims` | 1 commit, chưa hợp, còn đúng |
| Commit hoặc chép ra | `FIX-REPORT.md` (t9), 2 file spec/plan non-public-wave0 ở repo gốc | Chưa nằm trong git ở bất kỳ đâu |

### Ưu tiên 2 — trỏ đúng trunk cho người mới

| Việc | Ghi chú |
|---|---|
| Đổi default branch trên GitHub sang `codex/tri-region-color`, **hoặc** fast-forward `origin/main` lên trunk | Hiện `origin/HEAD → origin/main` khiến mọi clone nhận bản 2026-07-11 |
| Sửa `docs/HANDOFF.md` chỗ "Nhánh chính: `main`" | Đang sai, dẫn người mới đi nhầm |
| Ghi quy ước 3 gốc worktree vào `docs/HANDOFF.md` | Không đoán được |
| Chuyển checkout của repo gốc `C:\Code\vinhlong360` sang trunk | Đang đứng trên nhánh cũ hơn 278 commit |

### Ưu tiên 3 — hợp (theo thứ tự rẻ → đắt)

| Thứ tự | Nhánh | Độ khó | Ghi chú |
|---:|---|---|---|
| 1 | `fix/truthful-public-claims` | Thấp | 1 commit; bỏ phần FAQ ảnh đã lỗi thời; sửa lỗi §1.6/§1.7 đang chạy |
| 2 | `codex/phase4-multiday-allocation` | Thấp | chỉ 2/8 file đụng nhau |
| 3 | `codex/non-public-wave0` | Trung bình | 4/18 file đụng nhau; hợp sau np1 thì 3 commit doc tự tan |
| 4 | `codex/np1-identity-location-trust` | **Cao** | 19/58 file đụng nhau **và bắt buộc đánh số lại migration 071/072/073 → 076/077/078** |

### Ưu tiên 4 — bỏ (chỉ sau khi §Ưu tiên 1 xong)

| Đối tượng | Vì sao |
|---|---|
| 14 nhánh ở §4 | Đã xác nhận là tổ tiên của trunk, không còn gì riêng |
| `t7/crawler-pinned`, `claude/competent-northcutt-622292` | Trunk có bản tương đương **rộng hơn** (7 ca test + chốt chống fallback `httpx.get`) |
| `main` | Nằm trọn trong trunk. Chỉ bỏ **sau khi** đã quyết xong chuyện default branch ở Ưu tiên 2 |
| `stash@{0}` | Chỉ lệch 1 dòng comment, và trunk mới hơn |
| 15 worktree gắn nhãn "Rác" ở §5 | Sau khi đọc xong `FIX-REPORT.md` và `.superpowers/` |

---

## 8. Tự kiểm lại — các lệnh đã dùng để dựng tài liệu này

Tất cả đều **chỉ đọc**. Chạy từ bất kỳ worktree nào.

```bash
# trunk thật ở đâu: nhánh nào có nhiều commit riêng nhất so với main
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  echo "$(git rev-list --left-right --count main...$b)  $b"; done

# nhánh nào CÒN việc riêng thật (đo so với trunk, không phải main)
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  echo "$(git rev-list --left-right --count codex/tri-region-color...$b)  $b"; done

# nhánh nào mất được nếu máy hỏng
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  git merge-base --is-ancestor $b origin/codex/tri-region-color 2>/dev/null \
    && echo "ON-GITHUB   $b" || echo "LOCAL-ONLY  $b"; done

# đếm chính xác commit chỉ có trên máy
git rev-list --count $(git for-each-ref --format='%(refname:short)' refs/heads/ | tr '\n' ' ') \
  ^origin/main ^origin/codex/tri-region-color

# mặt va chạm khi hợp một nhánh
b=codex/np1-identity-location-trust; mb=$(git merge-base codex/tri-region-color $b)
comm -12 <(git diff --name-only $mb $b | sort) <(git diff --name-only $mb codex/tri-region-color | sort)

# worktree nào đang bẩn
git worktree list   # rồi: git -C <đường-dẫn> status --porcelain
```

**Cảnh báo về `git cherry` / `--cherry-mark`:** trên repo này chúng báo sai. Ba nhánh `t7/crawler-pinned`, `claude/competent-northcutt-622292`, `fix/truthful-public-claims` đều bị `git cherry` đánh `+` ("chưa có upstream"), nhưng hai cái đầu **đã** được thay thế trên trunk bằng bản viết lại. Patch-id không khớp vì code đã bị rebase/viết lại. Phải **đối chiếu nội dung thật** (grep marker, so tên test) mới kết luận được — đó là cách §3.4/§3.5 được kiểm.

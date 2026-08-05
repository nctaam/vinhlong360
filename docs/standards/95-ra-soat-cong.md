> STATUS (2026-08-05): active

# 95 — Rà soát cổng: cổng nào ĐỌC nội dung, cổng nào chỉ kiểm sự có mặt

Rà 28 cổng đang đăng ký trong `scripts/checks/` (19 module check + `common.py` + `run_hard.py` + `baseline_tool.py`).
Mỗi cổng bị hỏi đúng một câu: **nó đọc nội dung, hay chỉ kiểm sự có mặt của file / sự tồn tại của một dòng?**

Lý do rà: R20.5 (`api_contract`) từng chỉ hỏi "`docs/api-contract.md` có nằm trong danh sách file staged không". Stage một sửa đổi vu vơ là qua cổng; chế độ `--all` thì `return` rỗng nên cổng hạng HARD vô hiệu hoàn toàn ngoài lúc commit. Nó vừa được sửa (nay `--all` đối chiếu hợp đồng với route đọc từ AST). Tài liệu này đi tìm những cổng còn cùng bệnh.

Mọi con số dưới đây là **đo thật ngày 2026-08-05** trên worktree `tri-region-color`, bằng script thăm dò dựng fixture tạm ngoài repo (xem mục "Tự kiểm lại"). Không có con số nào chép lại từ tài liệu cũ.

## Cách phân loại

| Hạng | Nghĩa |
|---|---|
| **THẬT** | Đọc đúng thứ cần kiểm (nội dung file, AST, dữ liệu). Muốn qua cổng phải sửa đúng thứ cổng nói. Không tìm ra đường lách rẻ. |
| **YẾU** | Có đọc nội dung, nhưng tồn tại đường lách rẻ đã chứng minh được: phép đếm theo dòng, whitelist quá rộng, phạm vi hụt, hoặc fail-open khi thiếu công cụ. |
| **GIẢ** | Không đọc thứ cần kiểm. Chỉ kiểm file có mặt, hoặc trả rỗng ở chế độ đang chạy. |

Bốn vấn đề **xuyên suốt** (không tính vào hạng của cổng riêng lẻ, vì không cổng nào tự sửa được) nằm ở mục cuối.

## Bảng tổng — 28 cổng

| Rule | Check | Tầng | Hạng | Vì sao (một dòng) |
|---|---|---|---|---|
| R20.7 | `test_pairing` | soft-ratchet | ~~GIẢ~~ → **THẬT** ✅ | Lỗ file-rỗng đã vá `2c0f12bf`: file test phải có hàm `test_*` mới tính là cặp. *Đính chính:* `--all` trả rỗng là **cố ý** — R20.7 đối chiếu "file đổi ↔ test **staged**", khái niệm không tồn tại ngoài pre-commit; đây không phải lỗi |
| R30.6 | `axe` | ⚠️ chưa thực thi | **GIẢ** | Không nơi nào trong repo/CI sinh `axe-report.json` → vĩnh viễn 0. Đã hạ hạng trong `00-INDEX.md`; **cần chủ dự án quyết** có thêm axe scan vào CI hay không (kéo theo chromium ~300MB + phút CI) |
| R30.7 | `bundle` | soft-ratchet | ~~GIẢ~~ → **THẬT** ✅ | Đã vá: cổng nay chạy ở **job frontend** của `ci.yml` ngay sau `npm run build`, và exit 2 nếu thiếu `.output` thay vì im lặng trả 0 |
| R40.3 | `banned_claims` | hard | ~~YẾU~~ → **THẬT** ✅ | Lỗ miễn-trừ đã vá `cf7b84d9` |
| R10.6 | `banned_image_sources` | hard | ~~YẾU~~ → **THẬT** ✅ | Vi phạm thật ở `huong-dan.vue:459` đã sửa; lỗ miễn-trừ đã vá `cf7b84d9` — "không" chỉ miễn khi đi với động từ chỉ dẫn |
| R30.1 | `no_tailwind` | hard | ~~YẾU~~ → **THẬT** ✅ | Cùng bản vá `cf7b84d9` |
| R70.1 | `secrets` | hard | ~~YẾU~~ → **THẬT** ✅ | Đã vá: mọi biến thể `.env.*` (trừ bản mẫu) bị chặn tuyệt đối; `<...>` chỉ miễn khi là placeholder CHỮ HOA, không phải thẻ HTML. Giá phải trả: 0 vi phạm mới |
| R60.1 | `doc_status` | hard-ratchet | ~~YẾU~~ → **THẬT** ✅ | Đã vá `e84dbfb7`: STATUS phải CÓ nội dung. Cố ý không ép 4 trạng thái §3.6 — 44 file plan/QA dùng từ vựng superpowers hợp lệ |
| R10.7 | `tinh_cu` | hard-ratchet | ~~YẾU~~ → **THẬT** ✅ | Đã vá: whitelist thành `id<TAB>field<TAB>số_lần` và cổng ĐẾM suất; `_data_occurrences` quét đệ quy attributes lồng + itineraries. Lộ ra **8 vi phạm §1.6 THẬT** trong `attributes.key_facts[]` (một câu còn nói ngược sự thật hành chính) — đã sửa nội dung, không whitelist |
| R20.5 | `api_contract` | hard | ~~YẾU~~ → **THẬT** ✅ | Đã vá: đọc được `@router.get(HANG_SO)`; thêm **R20.5b** (hard-ratchet, baseline 275) cho chiều ngược code→hợp đồng |
| R30.3 | `fe_colors` | hard-ratchet | ~~YẾU~~ → **THẬT** ✅ | `count_matches=True` (270 dòng → 307 match, 37 suất ẩn) + roots thêm app.vue/error.vue. Kèm sửa bug lookahead khiến `rgb( var(--x) )` bị bắt oan |
| R30.2 | `fe_emoji` | soft-ratchet | ~~YẾU~~ → **THẬT** ✅ | Cùng bản vá (623 → 687, 64 suất ẩn) |
| R20.1 | `ruff_lint` | hard-ratchet | ~~YẾU~~ → **THẬT** ✅ | Đã vá: `--all` fail-closed khi thiếu ruff, staged cảnh báo ra stderr. CI job `test` nay cài ruff — trước đó không cài, nên cổng chưa từng chạy trong CI |
| R20.2 | `ruff_async` | hard-ratchet | ~~YẾU~~ → **THẬT** ✅ | Cùng bản vá |
| R50.4 | `thin_content` | soft-ratchet | ~~YẾU~~ → **THẬT** ✅ | Lên `soft-ratchet` (baseline 245): tầng `soft` thuần không bao giờ chặn. KHÔNG ép trả nợ cũ — §1.7 cấm độn chữ — chỉ chặn entity mỏng MỚI |
| R10.schema | `data_schema` | hard | THẬT | Parse data.json, đối chiếu enum thật từ `useConstants.ts`, bbox, id trùng |
| R10.3b | `data_typed_required` | hard-ratchet | THẬT | Gọi `entity_schemas.validate_attributes` — registry thật |
| R10.8 | `data_rich_source` | hard-ratchet | THẬT | Gọi `index_policy.decide_entity` + `source_policy` — fail-closed khi artifact hỏng |
| R20.3 | `bare_except` | soft-ratchet | THẬT | AST, đọc `utf-8-sig` nên không nuốt file BOM |
| R20.4 | `coverage` | soft-ratchet | THẬT | Đọc `coverage.json`; `--all` fail-closed khi thiếu artifact |
| R20.8 | `complexity` | soft-ratchet | THẬT | AST, đếm nhánh từng hàm |
| R20.9 | `policy_http_registry` | hard | THẬT | AST toàn `agent/`, khớp identity chính xác với registry, bắt cả entry registry chết |
| R20.10 | `entity image renderer registry` | hard | THẬT | Validate registry JSON + quét nguồn FE, fail-closed |
| R60.4 | `links` | hard-ratchet | THẬT | Mở từng link, thử theo cả thư mục file lẫn repo root |
| R50.2 | `content_fillers` | soft-ratchet | THẬT | Đi theo trường biên-tập của data.json, bỏ `source`; FE đếm từng match |
| R10.9 | `out_of_province` | soft-ratchet | THẬT | Như trên |
| R50.3 | `content_formula` | soft-ratchet | THẬT | Tách câu đầu/câu cuối rồi mới khớp |
| R50.7 | `content_superlative` | soft-ratchet | THẬT | Khớp theo câu, có kiểm dẫn chứng số trong cùng câu |

Tổng lúc rà (2026-08-05, sáng): **13 THẬT · 12 YẾU · 3 GIẢ**.
Sau đợt vá cùng ngày: **27 THẬT · 0 YẾU · 1 GIẢ** (R30.6 axe — chờ chủ dự án quyết), cộng rule mới **R20.5b**.

Các mục 1–2 bên dưới giữ nguyên văn bản lúc rà để đối chiếu; trạng thái mới nhất
nằm ở bảng tổng phía trên và ở `00-INDEX.md`.

---

## 1. Ba cổng GIẢ

### R20.7 — `test_pairing` (`scripts/checks/check_test_pairing.py:73`)

Cùng bệnh R20.5 cũ, gần như y nguyên.

- **Kiểm gì thật:** ở chế độ staged, với mỗi `agent/*.py` được stage, tìm trong tập staged một file `tests/test_*.py` mà **tên** khớp module, hoặc **import** module đó. Chỉ vậy.
- **`--all` trả rỗng:** thân hàm mở bằng `if files:` — `run(None)` rơi thẳng xuống `return count=0`. `run_hard --all` (pre-merge + CI) không bao giờ đánh giá R20.7.
- **Lách (staged):** tạo `tests/test_foo.py` chỉ có một dòng comment, stage cùng `agent/foo.py`. Cổng thấy tên khớp → qua. Không có hàm test nào, không có assert nào.
- **Cộng thêm:** tầng `soft-ratchet` nên còn được `SKIP_CHECKS` hợp lệ.
- **Bằng chứng:** `agent/foo.py` một mình → count 1 (chặn). Thêm `tests/test_foo.py` rỗng → count 0 (qua). `run(None)` → count 0.
- **Sửa tối thiểu:** (a) trong `--all`, đối chiếu toàn repo: mỗi `agent/*.py` phải có ít nhất một test import nó, đưa nợ hiện tại vào baseline làm ratchet; (b) ở staged, yêu cầu file test có ít nhất một `def test_*` **và** import/đụng tới module — parse AST đã sẵn trong `_test_candidates`, chỉ thêm điều kiện đếm hàm.

### R30.6 — `axe` (`scripts/checks/check_axe.py:48`)

- **Kiểm gì thật:** nếu `axe-report.json` tồn tại thì đọc đúng và đếm violation `serious|critical` (đã kiểm: dựng report giả có 1 lỗi critical → bắt được 1). Nếu không tồn tại → `count 0`.
- **Vấn đề:** **không nơi nào trong repo sinh file đó.** Tìm cả repo (loại `node_modules`) chuỗi `axe-core|axe-report|@axe`: chỉ có bản thân checker, `run_hard.py`, hai file tài liệu và một test. Không có dependency axe, không có script quét, không có bước CI. `00-INDEX.md:30` ghi "enforce CI" — thực tế không có gì để enforce.
- **Lách:** không cần lách. Cổng đã 0 sẵn.
- **Sửa tối thiểu:** hoặc (a) thêm bước sinh report rồi mới gọi `run_hard --all`, hoặc (b) nếu chưa làm nổi thì sửa `00-INDEX.md` cho đúng sự thật và hạ R30.6 xuống `pending-check` có hạn — đừng để một cổng hạng HARD nằm trong bảng mà không chạy bao giờ.

### R30.7 — `bundle` (`scripts/checks/check_bundle.py:46`)

- **Kiểm gì thật:** nếu có `web-nuxt/.output/public/_nuxt/*.js` thì gzip từng chunk, so ngân sách — logic đọc nội dung đàng hoàng.
- **Vấn đề:** job `test` trong `.github/workflows/ci.yml:97` chạy `run_hard --all` ngay sau pytest, **không build FE**. Không có `.output` → 0. Chỉ sống khi có người chạy `npm run build` rồi chạy cổng thủ công.
- **Sửa tối thiểu:** như R30.6 — hoặc gắn vào job có build, hoặc ghi đúng trạng thái vào INDEX.

---

## 2. Mười hai cổng YẾU

### R40.3 / R10.6 / R30.1 — `banned_claims` (`scripts/checks/check_banned_claims.py`) qua `NEG_DEFAULT` (`scripts/checks/common.py:20`)

`RegexCheck` bỏ **cả dòng** nếu dòng đó khớp `NEG_DEFAULT`. Biểu thức này (có `re.I`) chứa `KHÔNG` và `\bno\b`.

- **Lách 1:** viết câu cấm kèm chữ "không" ở bất kỳ đâu trên cùng dòng. Tiếng Việt thì "không" gần như dòng nào cũng có.
- **Lách 2:** `\bno\b` khớp cả trong `no-repeat`. Một dòng CSS/inline-style có `background: no-repeat` là miễn nhiễm với mọi pattern của cổng.
- **Bằng chứng:** `<p>Địa điểm này đã được xác minh.</p>` → count 1 (bắt). Cùng câu thêm ", không sai đâu" → count 0. Câu đó đặt trong `<p style='background:no-repeat'>` → count 0.
- **Đây không phải giả định:** hiện có một vi phạm thật đang bị che — `web-nuxt/pages/huong-dan.vue:459` trả lời người dùng rằng ảnh hiển thị khi có "nguồn bản quyền hợp lệ (UGC, Pexels, Unsplash)". Đúng thứ R10.6 sinh ra để chặn (CLAUDE.md §1.5), nhưng dòng có chữ "không" nên cổng đọc 0.
- **Sửa tối thiểu — hai phương án, giá đã đo trên repo thật:**
  - PA1: với file **không phải `.md`** thì `neg_context=None` (miễn-trừ chỉ dành cho văn xuôi tài liệu). Giá: R40.3 +0, R30.1 +0, R10.6 +1 — và cái +1 đó là vi phạm thật ở `huong-dan.vue:459`, không phải báo oan.
  - PA2: bỏ hai token dính nhầm `\bno\b` và `filler` khỏi `NEG_DEFAULT`. Giá đo được **y hệt PA1** (+0/+0/+1).
  - Cả hai đều gần như miễn phí. Đã kiểm tay 4 dòng `.md` mà `NEG_DEFAULT` đang miễn (`docs/b2g-pitch.md:3`, `:176`, `docs/claude-desktop/my-company.md:20`, `docs/content-creation-guide.md:57`): cả 4 là phủ định thật ("TUYỆT ĐỐI không thêm lại claim…") — nên giữ miễn-trừ cho `.md` là đúng.
- **Phạm vi hụt kèm theo:** R40.3 và R10.6 chỉ quét `web-nuxt/`, `agent/`, `scripts/`, `docs/` với glob `*.vue|*.ts|*.py|*.md`. Nội dung entity trong `web/data.json` **không** nằm trong tầm. Đã đo: gài `"summary": "ảnh lấy từ Wikimedia Commons"` vào data.json → count 0. Hiện data.json thật có 0 lần Wikimedia/Pexels/Unsplash, nên thêm `web/data.json` vào tầm quét tốn 0 vi phạm mới.

### R70.1 — `secrets` (`scripts/checks/check_secrets.py:14`, `:66`)

- **Lách 1 — `.env` biến thể:** cổng chỉ chặn tuyệt đối đường dẫn đúng bằng `.env` hoặc kết thúc `/.env`. `.env.production` không khớp, rồi rớt tiếp ở bộ lọc đuôi file (`*.py|*.ts|*.vue|*.js|*.json|*.sh|*.ps1`) → **không được quét một dòng nào**. Đã đo: `.env` staged → count 1; `.env.production` cùng nội dung → count 0.
- **Lách 2 — thẻ HTML:** `_ALLOW_LINE` chứa `<.*>`. Bất kỳ dòng nào có một cặp `<...>` đều được miễn. Đã đo: `API_KEY = "sk-live-…"` trong `agent/leak.py` → count 1; đúng chuỗi đó đặt trong `<div>…</div>` của một file `.vue` → count 0. Trong SFC Vue thì gần như dòng template nào cũng có thẻ.
- **Sửa tối thiểu:** (a) đổi điều kiện `.env` thành `Path(rel).name == ".env" or name.startswith(".env.")`, trừ `.env.example`; (b) thu `<.*>` thành dạng placeholder thật, ví dụ `<[A-Za-z_ -]{1,30}>`. **Giá đo được: 0 vi phạm mới trên repo hiện tại** cho vế (b) — sửa xong count vẫn 0.

### R60.1 — `doc_status` (`scripts/checks/check_doc_status.py:14`)

- **Kiểm gì thật:** 10 dòng đầu có dòng khớp `^>\s*\*{0,2}STATUS`. Không đọc giá trị.
- **Lách:** gõ đúng `> STATUS` rồi xuống dòng. Hoặc `> STATUSAAAA vớ vẩn`. Cả hai qua (đã đo: count 0; đối chứng thiếu hẳn header → count 1).
- **Sửa tối thiểu:** siết regex thành `^>\s*\*{0,2}STATUS[^\n]*\b(active|done|obsolete|superseded-by)\b` — đúng 4 trạng thái CLAUDE.md §3.6 đã chốt. Cần đo lại nợ trước khi bật vì baseline R60.1 hiện là 0 nhưng đó là số của luật lỏng.

### R10.7 — `tinh_cu` (`scripts/checks/check_tinh_cu.py:37`)

Cổng đọc nội dung thật, nhưng whitelist rộng hơn mô tả trong docstring ("per-occurrence").

- **Lách 1 — whitelist không đếm:** whitelist là tập cặp `(entity_id, field)`. Một cặp đã duyệt miễn **không giới hạn** số lần xuất hiện trong field đó. Đã đo: entity `e1` với 4 lần "tỉnh Bến Tre/Trà Vinh" trong `description`, whitelist đúng một dòng `e1<TAB>description` → count 0. Bỏ whitelist → count 4.
- **Lách 2 — vùng không quét:** chỉ duyệt `name`/`description`/`summary` và các `attributes` **kiểu chuỗi**. Attribute lồng (dict/list) và toàn bộ `itineraries` không đi qua. Trên data.json thật: **1** lần trong itineraries và **8** lần trong attributes không-phải-chuỗi, hiện không cổng nào nhìn thấy.
- **Số thật đáng chú ý:** whitelist đang có **88 cặp**, che **85/85** occurrence quét được. Nghĩa là R10.7 hiện không chặn gì cả; nó chỉ chặn *cặp mới*.
- **Sửa tối thiểu:** (a) đổi whitelist thành `entity_id<TAB>field<TAB>số_lần` và so đúng số lần; (b) mở rộng `_data_occurrences` đi đệ quy toàn bộ `attributes` và `itineraries` — dùng luôn `_walk_authored` của `check_content_voice.py:45` để khỏi viết bộ duyệt thứ hai.

### R20.5 — `api_contract` (`scripts/checks/check_api_contract.py:176`)

Bản vá đã đúng hướng: `--all` nay đọc AST toàn `agent/`, ghép prefix `APIRouter`, và bắt entry hợp đồng mô tả route đã biến mất. Còn ba khe:

- **Khe 1 — thiếu chiều ngược ở `--all`:** `run(None)` chỉ chạy `_stale_contract_entries` (hợp đồng → code). Route có trong code mà hợp đồng không nhắc thì `--all` không thấy. Đã đo trên fixture: thêm `@router.get("/khong-he-co-trong-hop-dong")`, hợp đồng để trống → count 0.
- **Khe 2 — path là hằng số:** `@router.get(P)` với `P = "/an-danh"` không lọt vào `_decorated_paths` (chỉ nhận `ast.Constant`), cũng không lọt `ROUTE_RE` ở chế độ staged (đòi literal trong ngoặc kép cùng dòng).
- **Khe 3 — khớp bằng substring:** ở chế độ staged, điều kiện đủ là chuỗi path xuất hiện **ở bất kỳ đâu** trong `docs/api-contract.md`, kể cả trong code fence hay câu không liên quan.
- **Số thật để cân nhắc:** đọc được **367** route từ `agent/`, trong đó **297** không xuất hiện trong hợp đồng. Nên chiều ngược **không thể** bật ở tầng hard = 0.
- **Sửa tối thiểu:** thêm một rule mới (ví dụ `R20.5b`, `hard-ratchet`, baseline = 297) đếm route-không-được-mô-tả trong `--all`. Ratchet giữ đúng tinh thần bộ chuẩn: nợ cũ không phải trả ngay, nhưng route mới bắt buộc có mô tả.

### R30.3 / R30.2 — `fe_tokens` (`scripts/checks/check_fe_tokens.py`, phép đếm ở `scripts/checks/common.py:179`)

- **Lách — đếm theo dòng:** `RegexCheck` (nhánh mặc định) ghi **một** violation cho mỗi dòng có khớp, không phải mỗi match. Đã đo: 3 màu hex trên 3 dòng → count 3; đúng 3 màu đó gộp một dòng → count 1. Emoji y hệt: 2 emoji / 2 dòng → 2; gộp một dòng → 1.
- **Vì sao nguy:** đây là ratchet. Gộp dòng vài chỗ cũ là mua được "hạn mức" cho màu cứng mới ở chỗ khác mà tổng vẫn không tăng. Ratchet chỉ nhìn tổng (`scripts/checks/common.py:207`).
- **Sửa tối thiểu:** bật `count_matches=True` cho hai check này (đã có sẵn tham số) — nhưng phải đo lại baseline trong cùng commit vì count sẽ nhảy.
- **Phạm vi hụt (nhẹ):** roots chỉ có `pages/`, `components/`, `layouts/`. `web-nuxt/app.vue` và `web-nuxt/error.vue` nằm ngoài. Đã đo: hiện cả hai file có 0 màu ngoài token, nên thêm vào roots tốn 0.

### R20.1 / R20.2 — `ruff` (`scripts/checks/check_ruff.py:24`, `:49`)

- **Kiểm gì thật:** gọi `ruff check --output-format json` và đếm — đọc nội dung thật (đã đo: file có `F821` → count 2).
- **Fail-open:** không tìm thấy ruff → `return []` → count 0, không một dòng cảnh báo. Đã đo bằng cách ép `find_ruff()` trả `None`: file lỗi vẫn cho count 0. Tương tự, ruff chạy lỗi khiến stdout rỗng cũng thành 0.
- **Mức nguy thực tế:** trên CI thì `ruff>=0.9` nằm trong `requirements.txt` và job `test` cài trước khi chạy `run_hard --all`, nên CI có răng. Lỗ này chỉ ăn vào hook local trên máy thiếu ruff — nhưng hook local chính là thứ dev tin.
- **Sửa tối thiểu:** khi `find_ruff()` trả `None`, ở chế độ `--all` phát một violation "không đo được"; ở chế độ staged in một dòng cảnh báo thay vì im lặng.

### R50.4 — `thin_content` (`scripts/checks/check_thin_content.py:14`)

Đọc nội dung đúng (đếm ký tự `summary+description`), nhưng tầng `soft`: `run_hard` chỉ chặn `hard` và các `*-ratchet`. Rule soft thuần **không bao giờ chặn gì**, kể cả tăng vọt. Nợ hiện tại 245 entity. Nếu muốn nó có răng thì đổi sang `soft-ratchet`; nếu cố ý chỉ để theo dõi thì nên ghi rõ điều đó trong `00-INDEX.md` để không ai tưởng có cổng.

---

## 3. Mười ba cổng THẬT — vì sao xếp vào đây

- **R20.9 `policy_http_registry`** — mạnh nhất bộ. Parse AST toàn `agent/`, dựng lại prefix router, chỉ tính route thật sự được mount vào `app` của `agent/server.py`, khớp identity `(method, path, route_name)` chính xác với `POLICY_ENDPOINTS`, và bắt cả chiều ngược (entry registry không còn route). Đúng loại cổng mà bài học "route khai hai lần vẫn xanh" đòi hỏi.
- **R20.10 `entity image renderer registry`** — validate schema registry JSON rồi quét từng file nguồn FE tìm sink ảnh không qua descriptor. Fail-closed.
- **R10.schema / R10.3b / R10.8** — parse data.json thật; enum type đọc từ `useConstants.ts` (không chép cứng); required per-type gọi `entity_schemas`; RICH gọi `index_policy` + `source_policy`, và nếu artifact policy hỏng thì báo vi phạm chứ không nuốt.
- **R20.8 / R20.3** — AST thật, đọc `utf-8-sig` nên file có BOM không bị bỏ qua âm thầm.
- **R20.4 `coverage`** — đọc `coverage.json`; thiếu artifact thì **`--all` báo vi phạm** (fail-closed) chứ không skip như axe/bundle. Đúng cách làm; hai cổng GIẢ ở trên nên bắt chước.
- **R60.4 `links`** — mở từng target, thử theo hai gốc, bỏ code fence và inline code. (Không kiểm anchor `#...`, nhưng đó là giới hạn đã ghi rõ, không phải lỗ.)
- **R50.2 / R10.9 / R50.3 / R50.7** — đi theo trường biên-tập của data.json, loại `source`/metadata; FE đếm từng match (`count_matches=True`) nên không dính lỗ gộp-dòng.

---

## 4. Bốn vấn đề xuyên suốt

**A. Ratchet cộng dồn cho phép bù trừ.** `ratchet_violations` (`scripts/checks/common.py:207`) so **tổng toàn repo** với baseline. Xoá một vi phạm ở file A rồi thêm một cái ở file B → tổng không đổi → 0 blocker (đã đo). Với các rule nợ lớn (R30.2 = 623, R30.3 = 270, R50.2 = 102) thì cửa này rất rộng. `scripts/scorecard.py:35` còn cộng dồn thêm một bậc — theo **chiều** — nên vi phạm R30.3 mới có thể được bù bằng việc dọn emoji R30.2. Sửa được: ratchet theo `(rule, file)` thay vì theo rule; nhưng đó là thay đổi lớn, cần chủ dự án quyết.

**B. Không ai canh `baseline.json`.** Chỉ `common.load_baseline` đọc và `baseline_tool --write` ghi. `pre_merge_check.py` không so baseline với HEAD, `scorecard.py` cũng không. Một commit chạy `baseline_tool --write` rồi commit kèm là hợp thức hoá toàn bộ nợ mới, mọi ratchet im lặng. Quy tắc "chỉ cập nhật baseline kèm giải trình" hiện là **quy ước, không phải cổng**. Sửa tối thiểu: thêm bước pre-merge so `baseline.json` với bản ở nhánh gốc và bắt buộc có dòng giải trình trong `90-exceptions-log.md` khi có số nào tăng.

**C. Mọi cổng dữ liệu/nội dung chỉ nhìn `web/data.json`.** Chín rule (R10.schema, R10.3b, R10.7, R10.8, R10.9, R50.2, R50.3, R50.4, R50.7) đọc bản export 4.4 MB. Theo CLAUDE.md §1.1 thì DB mới là nguồn sự thật và data.json **đã phân kỳ**; entity sửa qua AdminCP write-through không đi qua file này. Nghĩa là các cổng nội dung đang canh cửa sau. Không cổng nào tự sửa được — cần quyết định riêng về đường export DB → data.json.

**D. Cổng dựa vào artifact chỉ sống nếu ai đó sinh artifact.** R30.6 (axe) không có nguồn sinh trong toàn repo; R30.7 (bundle) có nguồn sinh nhưng job CI chạy cổng lại không build; R20.4 (coverage) được CI sinh trước và fail-closed khi thiếu. Ba cách xử lý khác nhau cho cùng một dạng cổng. Nên thống nhất theo kiểu R20.4.

**Quan sát phụ:** bảng `00-INDEX.md` đã lệch với `baseline.json` (INDEX ghi R20.1=80, R20.8=250, R30.3=1373, R50.2=389, R60.1=29, R10.3b=49; file máy ghi 0/14/289/102/0/0), và thiếu hẳn R20.10. Khi hai bảng lệch thì file máy là cái có hiệu lực — INDEX đang nói quá về mức nợ.

---

## 5. Thứ tự nên sửa

1. **Rẻ và đóng lỗ thật ngay** — giá đã đo là 0 hoặc 1: `.env.*` + `<.*>` của R70.1; `NEG_DEFAULT` (PA1 hoặc PA2) của R40.3/R10.6/R30.1; thêm `web/data.json` vào tầm quét R10.6.
2. **Cổng đang không chạy** — R20.7 (`--all` rỗng + test rỗng vẫn qua), R30.6, R30.7. Hoặc làm cho chạy, hoặc hạ hạng trong INDEX. Đừng để bảng chuẩn ghi "hard" cho thứ vĩnh viễn bằng 0.
3. **Cần đo lại baseline trong cùng commit** — `count_matches` cho R30.3/R30.2, siết `> STATUS` của R60.1, whitelist có đếm của R10.7, `R20.5b` chiều ngược với baseline 297.
4. **Cần chủ dự án quyết** — ratchet theo file (A), cổng canh `baseline.json` (B), đường export DB → data.json (C).

---

## 6. Tự kiểm lại

Cách đo trong tài liệu này: dựng thư mục fixture tạm **ngoài repo**, ghi file có vi phạm đã biết, rồi gọi thẳng `Check.run(files)` và `Check.run(None)` với `root` trỏ vào fixture — không chạm repo, không chạy git. Ví dụ:

```python
import sys, tempfile
from pathlib import Path
sys.path.insert(0, "scripts")
from checks import check_secrets

tmp = Path(tempfile.mkdtemp())
(tmp / ".env.production").write_text('ADMIN_API_KEY="sk-live-9f3ba2d81c4e77a0b5d6e9f1"\n', encoding="utf-8")
print(check_secrets.SecretsCheck(root=tmp).run([".env.production"])["count"])  # -> 0
```

Số toàn repo lấy bằng hai lệnh đọc-thuần (không `--write`):

```
python scripts/checks/baseline_tool.py     # bảng count theo rule, chế độ --all
python scripts/checks/run_hard.py --all    # kết luận chặn/không chặn
```

Trạng thái lúc rà (worktree `tri-region-color`, 2026-08-05): `run_hard --all` **chặn** với hai blocker ratchet — R20.8 = 28 > baseline 14 (28 vi phạm ở 7 file, nhiều nhất `agent/gpt55_quality_burst.py` 11) và R20.4 = 1 > 0 (chưa sinh `coverage.json` ở máy local; CI sinh trước khi chạy cổng nên không dính). Nguyên nhân R20.8 lệch baseline **chưa xác minh** — có thể do nhánh này khác `main`, không nên coi là kết luận.

Bộ test của chính các cổng: `python -m pytest tests/checks -q` → **128 passed**. Đáng lưu ý: 128 test này xanh trong khi mọi lỗ liệt kê ở trên vẫn tồn tại — đúng bài học "test đông không bằng test đúng tầng". Và `tests/checks/test_hard_checks.py:247` vẫn còn một test kiểu `inspect.getsource()` (assert chuỗi import có trong source hàm) — loại test đỏ khi refactor đúng, xanh khi hành vi sai. Đừng viết thêm.

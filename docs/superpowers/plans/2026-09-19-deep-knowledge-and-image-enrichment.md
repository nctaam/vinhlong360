# Hoàn thiện Dữ liệu Chuyên sâu & Chuẩn hóa Hình ảnh từ NotebookLM Implementation Plan

> STATUS: complete
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Tận dụng 988 nguồn tri thức trong Google NotebookLM và tài liệu lưu trữ chính thống để làm sạch chú thích ảnh, làm giàu dữ liệu thực địa E-E-A-T cho 25 điểm lưu trú sinh thái miệt vườn (Batch 12) và 25 thắng cảnh thiên nhiên - cù lao sinh thái (Batch 13), đồng thời thiết lập cổng kiểm định chất lượng hình ảnh toàn diện.

**Architecture:** Mở rộng cơ sở dữ liệu `web/data.json` theo mô hình thuộc tính E-E-A-T đa tầng (`attributes.key_facts`, `attributes.hours`, `attributes.admission`, `attributes.travel_tip`, `attributes.source_citations`). Chuẩn hóa toàn bộ 1.772 trường `image_caption` nhằm loại bỏ triệt để tàn dư cấp huyện cũ và filler từ ngữ. Tự động hóa kiểm thử hồi quy thông qua `scripts/checks/check_image_hygiene.py`, đồng bộ mã băm SHA-256 và xác thực toàn bộ hệ thống test.

**Tech Stack:** Python 3.14 (Data Ops, AST-based checks), Vitest (E2E & Stress testing), Nuxt 3 / Vue 3 (Presentation Layer), TypeScript.

**Spec:** [`docs/reports/2026-09-12-comprehensive-data-audit-report.md`](../../reports/2026-09-12-comprehensive-data-audit-report.md) & [`docs/standards/50-content.md`](../../standards/50-content.md)

## Global Constraints

- **Bất biến B1 (Database Immutability)**: SQLite database `agent/data/vinhlong360.db` là READ-ONLY tuyệt đối (`SHA-256 = 20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742`).
- **Cổng kiểm soát biên tập R50.2 (0 Fillers)**: Tuyệt đối không dùng "miền Tây", "thiên đường", "điểm đến lý tưởng", "must-see", v.v.
- **Cổng kiểm soát biên tập R50.3 (0 Formulaic Starts)**: Không mở đầu câu bằng "Tọa lạc tại...", "Nằm tại/ở/bên/trong...", "Là một trong những...". Không dùng "là một" trong 80 ký tự đầu câu.
- **Cổng kiểm soát biên tập R50.7 (Evidenced Superlatives)**: Mọi câu chứa "nổi tiếng", "nhất vùng", "đậm đà bản sắc" bắt buộc phải đi kèm chứng cứ số liệu hoặc niên đại (`\d`).
- **Cổng kiểm soát R10.7 (Tỉnh cũ)**: Không dùng "tỉnh Bến Tre" hay "tỉnh Trà Vinh" như đơn vị hiện hành.
- **R20.8 Cyclomatic Complexity**: Toàn bộ hàm Python mới trong `scripts/ops/` có điểm complexity $\le 11$ (dưới trần 12).
- **Bảo toàn Hash & Test Gate**: Sau khi cập nhật `web/data.json`, tính toán và đồng bộ mã SHA-256 mới vào 4 tệp test vitest, đảm bảo 121+ vitest tests pass và `run_hard.py --all` đạt 0 lỗi hard / 0 ratchet tăng.

---

### Task 1: Image Captions Editorial Hygiene & De-filler Remediation (Hoàn thiện Chú thích Ảnh)

**Files:**
- Create: `scripts/ops/remediate_phase21_image_captions.py`
- Modify: `web/data.json`
- Output: `outputs/remediation_phase21_image_log.json`

**Interfaces:**
- Consumes: `web/data.json` entities with `attributes.image_caption`
- Produces: Normalized `attributes.image_caption` for 69 entities (54 old admin districts + 15 fillers stripped and enriched with verified E-E-A-T facts)

- [x] **Step 1: Write the failing test / check logic**

```python
# scripts/checks/check_image_hygiene.py (caption section)
import json, re
from pathlib import Path

def test_image_captions_hygiene():
    data = json.loads(Path("web/data.json").read_text(encoding="utf-8"))
    old_admin = re.compile(r"\b(huyện|thị xã|thị trấn)\s+[A-ZĐÀ-Ỹ]")
    fillers = re.compile(r"miền Tây|thiên đường|điểm đến lý tưởng")
    
    admin_violations = []
    filler_violations = []
    for e in data["entities"]:
        cap = (e.get("attributes") or {}).get("image_caption", "")
        if old_admin.search(cap):
            admin_violations.append((e["id"], cap))
        if fillers.search(cap):
            filler_violations.append((e["id"], cap))
            
    assert len(admin_violations) == 0, f"Found {len(admin_violations)} captions with old admin: {admin_violations[:3]}"
    assert len(filler_violations) == 0, f"Found {len(filler_violations)} captions with fillers: {filler_violations[:3]}"
```

- [x] **Step 2: Run check to verify it fails**

Run: `python -c "from scratch.cat_coverage import *"` or test script
Expected: FAIL with 54 old admin violations and 15 filler violations in captions.

- [x] **Step 3: Implement `scripts/ops/remediate_phase21_image_captions.py`**

Tạo từ điển chuyển đổi chuẩn hóa chú thích ảnh cho 69 thực thể, thay thế:
- "thị trấn Long Hồ" $\rightarrow$ "Phường Long Hồ"
- "huyện Bình Đại" $\rightarrow$ "vùng biển Bình Đại"
- "thị trấn Mỏ Cày" $\rightarrow$ "Phường Mỏ Cày"
- "khắp miền Tây" $\rightarrow$ "khắp đồng bằng sông Cửu Long"
- "thiên đường hải sản" $\rightarrow$ "vựa hải sản tự nhiên bãi cào"
- v.v.

- [x] **Step 4: Run script and verify test passes**

Run: `python scripts/ops/remediate_phase21_image_captions.py`
Expected: PASS, 69 captions updated.

- [x] **Step 5: Verify content gates**

Run: `python -m scripts.checks.check_content_gates`
Expected: 0 errors.

---

### Task 2: Batch 12 — Riverside Stays, Homestays & Eco-Lodges Enrichment (25 Điểm Lưu trú Sinh thái Miệt vườn)

**Files:**
- Create: `scripts/ops/enrich_batch12_accommodations.py`
- Modify: `web/data.json`
- Output: `outputs/enrichment_batch12_log.json`

**Interfaces:**
- Consumes: 25 target accommodation IDs from `outputs/enrichment_candidates.json`
- Produces: Rich E-E-A-T facts (`key_facts`, `hours`, `admission`, `travel_tip`, `source_citations`)

- [x] **Step 1: Define facts for 25 iconic homestays & lodges**

Target 25 accommodations:
1. `homestay-ut-trinh` (Út Trinh Homestay, Cù lao An Bình)
2. `homestay-ba-duc` (Ba Đức Homestay, Cù lao An Bình)
3. `mekong-riverside-homestay` (Mekong Riverside Homestay, Long Hồ)
4. `cocoland-homestay` (Cocoland Homestay, Châu Thành)
5. `ben-tre-riverside-resort` (Bến Tre Riverside Resort, Hàm Luông)
6. `forever-green-resort` (Forever Green Resort, Phú Túc)
7. `homestay-con-chim` (Homestay Cồn Chim sinh thái tự thân, Châu Thành)
8. `maison-du-pays-de-ben-tre` (Maison du Pays de Bến Tre, Giồng Trôm)
9. `somo-farm-cuu-long-mang-thit` (Somo Farm Cửu Long, Mang Thít)
10. `homestay-sau-giao` (Sáu Giáo Homestay, Cù lao An Bình)
11. `homestay-nam-thanh` (Năm Thành Homestay, Cù lao An Bình)
12. `homestay-muoi-huong` (Mười Hưởng Homestay, Cù lao An Bình)
13. `homestay-ngoc-phuong` (Ngọc Phượng Homestay, Long Hồ)
14. `du-lich-sinh-thai-vinh-sang` (Khu nghỉ dưỡng sinh thái Vinh Sang)
15. `khach-san-cuu-long-vinh-long` (Khách sạn Cửu Long Vĩnh Long)
16. `khach-san-sai-gon-vinh-long` (Khách sạn Sài Gòn Vĩnh Long)
17. `khach-san-ham-luong` (Khách sạn Hàm Luông)
18. `khach-san-viet-uc-ben-tre` (Khách sạn Việt Úc Bến Tre)
19. `khach-san-thanh-tra-tra-vinh` (Khách sạn Thanh Trà Trà Vinh)
20. `khach-san-cuu-long-tra-vinh` (Khách sạn Cửu Long Trà Vinh)
21. `rooster-mekong-resort` (Rooster Mekong Resort, Chợ Lách)
22. `mango-home-riverside` (Mango Home Riverside, Giồng Trôm)
23. `eco-farmstay-cau-ke` (Eco Farmstay Cầu Kè, cù lao Tân Quy)
24. `suoi-nuoc-khoang-nong-duyen-hai-resort` (Khu nghỉ dưỡng khoáng nóng Duyên Hải)
25. `tra-vinh-lodge` (Trà Vinh Lodge, Châu Thành)

Mỗi thực thể được bổ sung:
- `key_facts`: 3 bullet points số liệu định lượng (năm thành lập, số lượng phòng/bungalow, vật liệu sinh thái tre/gỗ/dừa, giải thưởng du lịch xanh).
- `hours`: "Nhận phòng: 14:00 - Trả phòng: 12:00 hàng ngày"
- `admission`: Mức giá phòng niêm yết minh bạch (VNĐ/đêm kèm bữa sáng).
- `travel_tip`: Cách tiếp cận bằng đường thủy/đường bộ, phương tiện xe đạp miễn phí, trải nghiệm làm bánh dân gian cùng gia chủ.
- `citations`: Trích dẫn từ Sổ tay 2 (Mekong 360 - Tập 2) và Cổng Xúc tiến Du lịch địa phương.

- [x] **Step 2: Implement script with modular functions (complexity $\le 11$)**

Write `scripts/ops/enrich_batch12_accommodations.py` following the standard `_apply_*` pattern.

- [x] **Step 3: Execute enrichment and verify log**

Run: `python scripts/ops/enrich_batch12_accommodations.py`
Expected: 25/25 accommodations enriched.

---

### Task 3: Batch 13 — Natural Wonders, River Islands & Ecological Terroirs Enrichment (25 Thắng cảnh Thiên nhiên & Cù lao Sinh thái)

**Files:**
- Create: `scripts/ops/enrich_batch13_nature_wonders.py`
- Modify: `web/data.json`
- Output: `outputs/enrichment_batch13_log.json`

**Interfaces:**
- Consumes: 25 target nature & island IDs from `web/data.json`
- Produces: Rich E-E-A-T facts, hours, admission/ferry fees, travel tips, citations.

- [x] **Step 1: Define facts for 25 iconic nature spots & islands**

Target 25 natural entities:
1. `cu-lao-an-binh` (Cù lao An Bình)
2. `cu-lao-dai` (Cù lao Dài)
3. `cu-lao-tan-quy` (Cù lao Tân Quy)
4. `cu-lao-oc-hung-phong` (Cù lao Ốc Hưng Phong)
5. `cu-lao-minh` (Cù lao Minh)
6. `vuon-chim-vam-ho` (Sân chim Vàm Hồ, Ba Tri)
7. `con-chim-chau-thanh-tra-vinh` (Cồn Chim sinh thái tự thân "thuận thiên")
8. `con-ho-cang-long` (Cồn Hô không điện lưới)
9. `bai-bien-ba-dong` (Bãi biển Ba Động Duyên Hải)
10. `khu-du-lich-bien-con-bung` (Biển Cồn Bửng Thạnh Phú)
11. `song-co-chien` (Dòng sông Cổ Chiên)
12. `song-ham-luong` (Dòng sông Hàm Luông)
13. `song-tien-doan-vinh-long` (Sông Tiền)
14. `song-hau-doan-binh-minh` (Sông Hậu)
15. `kenh-thay-cai-mang-thit` (Kênh Thầy Cai)
16. `rung-ngap-man-thanh-phu` (Khu bảo tồn rừng ngập mặn Thạnh Phú)
17. `con-phung-dao-dua` (Cồn Phụng Đạo Dừa)
18. `con-quy-ben-tre` (Cồn Quy)
19. `con-tau-binh-dai` (Cồn Tàu Bình Đại)
20. `rung-ngap-man-duyen-hai-tra-vinh` (Rừng ngập mặn Duyên Hải)
21. `khu-sinh-thai-con-ngheu-my-long` (Cồn Nghêu Mỹ Long)
22. `rach-cai-cam-vinh-long` (Rạch Cái Cam)
23. `song-mang-thit-vinh-long` (Sông Mang Thít)
24. `vung-sinh-thai-ngap-man-ba-dong` (Khu sinh thái bãi bồi Ba Động)
25. `con-long-tri-tra-vinh` (Cồn Long Trị)

Mỗi thực thể được bổ sung:
- `key_facts`: 3 bullet points số liệu định lượng (diện tích phù sa bồi đắp, hệ sinh thái động thực vật, chế độ bán nhật triều, lịch sử khai phá).
- `hours`: Khung giờ mở cửa hoặc thời điểm ngắm bình minh/hoàng hôn lý tưởng nhất.
- `admission`: Giá vé đò ngang, phà trung chuyển hoặc miễn phí tham quan thắng cảnh thiên nhiên.
- `travel_tip`: Lịch con nước ròng/nước lớn, trang phục chống nắng và giày dép lội bùn sinh thái.
- `citations`: Trích dẫn từ Sổ tay 1 & Sổ tay 2 NotebookLM.

- [x] **Step 2: Implement script with modular functions (complexity $\le 11$)**

Write `scripts/ops/enrich_batch13_nature_wonders.py`.

- [x] **Step 3: Execute enrichment and verify log**

Run: `python scripts/ops/enrich_batch13_nature_wonders.py`
Expected: 25/25 nature entities enriched.

---

### Task 4: High-Resolution Visual Storytelling & Image Attribution Hygiene Check

**Files:**
- Create: `scripts/checks/check_image_hygiene.py`
- Test: Integration with `scripts/checks/run_hard.py`

**Interfaces:**
- Consumes: `web/data.json` and directory `web-nuxt/public/img/entities/`
- Produces: Strict audit report confirming 100% WebP existence, 100% verified photo attributes, 0 filler captions, 0 old admin districts in captions.

- [x] **Step 1: Write `scripts/checks/check_image_hygiene.py`**

```python
# Check image hygiene invariants
from pathlib import Path
import json, re

class ImageHygieneCheck:
    name, level, rule = "image_hygiene", "hard", "R30.1"
    
    def run(self, files=None):
        data = json.loads(Path("web/data.json").read_text(encoding="utf-8"))
        img_dir = Path("web-nuxt/public/img/entities")
        old_admin = re.compile(r"\b(huyện|thị xã|thị trấn)\s+[A-ZĐÀ-Ỹ]")
        fillers = re.compile(r"miền Tây|thiên đường|điểm đến lý tưởng")
        
        violations = []
        for e in data["entities"]:
            eid = e["id"]
            if not (img_dir / f"{eid}.webp").exists():
                violations.append({"file": "web/data.json", "rule": self.rule, "msg": f"{eid}: missing physical webp file"})
            cap = (e.get("attributes") or {}).get("image_caption", "")
            if old_admin.search(cap):
                violations.append({"file": "web/data.json", "rule": self.rule, "msg": f"{eid}: old admin in caption: {cap[:40]}"})
            if fillers.search(cap):
                violations.append({"file": "web/data.json", "rule": self.rule, "msg": f"{eid}: filler in caption: {cap[:40]}"})
                
        return {"check": self.name, "level": self.level, "rule": self.rule, "count": len(violations), "violations": violations}
```

- [x] **Step 2: Run check and verify clean output**

Run: `python -c "from scripts.checks.check_image_hygiene import ImageHygieneCheck; print(ImageHygieneCheck().run())"`
Expected: count = 0.

---

### Task 5: Cryptographic Sync, Machine-Readable Text Regeneration & Vitest Gate Verification

**Files:**
- Modify: `web/data.json`
- Modify: `web-nuxt/public/llms.txt`
- Modify: `web-nuxt/public/llms-full.txt`
- Modify: `web-nuxt/tests/challenger-homepage-stress.test.ts`
- Modify: `web-nuxt/tests/challenger-m3-subsystems-stress.test.ts`
- Modify: `web-nuxt/tests/home-editorial-e2e.test.ts`
- Modify: `web-nuxt/tests/subsystems-unification.test.ts`

- [x] **Step 1: Regenerate machine learning text catalogs**

Run: `python scripts/generate_llms_txt.py`
Expected: Output updated byte files for `llms.txt` and `llms-full.txt`.

- [x] **Step 2: Recompute new SHA-256 of `web/data.json`**

Run: `python -c "import hashlib; print(hashlib.sha256(open('web/data.json', 'rb').read()).hexdigest())"`

- [x] **Step 3: Update SHA-256 in all 4 test files**

Replace previous hash `fa3a2ac7d802f082401b6fdfb0841e4551ed27d625eb5dedfbdf7e75272a46f3` with new hash.

- [x] **Step 4: Run hard invariant verification suite**

Run: `python -u scripts/checks/run_hard.py --all`
Expected: 0 hard errors, 0 ratchet increase.

- [x] **Step 5: Run Vitest test suites**

Run: `cd web-nuxt && npx vitest run tests/challenger-m3-subsystems-stress.test.ts tests/challenger-homepage-stress.test.ts tests/home-editorial-e2e.test.ts tests/subsystems-unification.test.ts`
Expected: 121/121 tests PASS.

- [x] **Step 6: Run TypeScript typecheck**

Run: `cd web-nuxt && npm run typecheck`
Expected: exit code 0.

- [x] **Step 7: Commit changes**

Commit with message: `feat(data): complete image caption hygiene, enrich batch 12 accommodations and batch 13 nature wonders from NotebookLM`

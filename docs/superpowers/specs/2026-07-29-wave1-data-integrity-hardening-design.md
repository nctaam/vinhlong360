# Wave 1 - gia cố tính toàn vẹn dữ liệu entity

> STATUS: approved-design

**Ngày:** 2026-07-29

**Phạm vi:** chỉ triển khai và kiểm thử trên workspace/local hoặc PostgreSQL disposable

**Cấm trong task này:** SSH/VPS, kết nối production, áp migration production, sửa hoặc đối soát dữ liệu production

## 1. Bối cảnh

Đợt rà soát chỉ đọc cho thấy code và production có một số khoảng trống cần đóng trước khi làm sạch dữ liệu:

- PostgreSQL production đang ở schema version 70 nhưng thiếu hai trigger rating `trg_entity_ratings` và `trg_entity_ratings_del`.
- `sync_entity_details()` chỉ ghi bảng CTI hiện tại, chưa xóa hàng thuộc kind cũ khi entity đổi type/kind.
- Detail cache có thể âm thầm ghi đè nếu một entity xuất hiện trong nhiều bảng CTI.
- Một số script có thể ghi trực tiếp `entities.attributes`, bỏ qua đường đồng bộ typed columns/CTI.
- Runtime production chỉ kiểm tra khóa bí mật khi `ENVIRONMENT=production`; file cấu hình deployment thiếu biến này có thể bị hiểu là development.
- Công cụ parity hiện tại in giá trị cụ thể, không phù hợp làm readiness/invariant report an toàn.

Wave 1 xây hàng rào kỹ thuật và khả năng kiểm chứng. Đợt này không tự sửa dữ liệu lịch sử và không thay đổi production.

## 2. Mục tiêu và bất biến

Wave 1 phải bảo đảm các bất biến sau:

1. Mọi lần ghi entity qua API dữ liệu chuẩn đều đồng bộ atomically hàng `entities`, universal columns và đúng một bảng CTI.
2. Sau khi entity đổi kind, không còn hàng CTI thuộc kind cũ.
3. Cache chỉ phản ánh transaction đã commit và không che giấu entity nằm trong nhiều bảng CTI.
4. Production không được khởi động với SQLite, thiếu PostgreSQL DSN hoặc tắt `ENTITY_DETAILS_TABLES`.
5. Deployment authority dùng cho production phải khai báo tường minh `ENVIRONMENT=production`.
6. PostgreSQL readiness phải kiểm tra schema version và các trigger bắt buộc mà release phụ thuộc.
7. Repository test phải chặn đường ghi trực tiếp mới vào `entities.attributes` ngoài danh sách ngoại lệ tối thiểu, có chủ đích.
8. Verifier chỉ đọc chỉ xuất số lượng tổng hợp; không in tên, nội dung, địa chỉ, attributes hoặc connection string.
9. Migration mới phải additive, xác định, kiểm thử được và chưa được áp lên production trong task này.

## 3. Các phương án đã cân nhắc

### 3.1. Gia cố tập trung trong kiến trúc hiện tại - chọn

Bổ sung validator, trigger readiness, CTI cleanup/cache staging, source guard, verifier chỉ đọc và migration `071` trong các module hiện có. Phương án này đóng đúng các lỗ hổng đã quan sát với phạm vi thay đổi nhỏ nhất và ít rủi ro hồi quy nhất.

### 3.2. Tạo entity mutation service mới - để sau

Một service mới có thể tạo ranh giới ghi sạch hơn, nhưng sẽ buộc đổi nhiều caller, script và test trong cùng một wave. Chỉ thực hiện sau khi source guard đã cung cấp inventory ổn định và có kế hoạch migration caller riêng.

### 3.3. Bắt buộc ghi qua PostgreSQL procedures/roles - để sau

Database procedures và quyền role có thể ngăn ghi sai ngay tại DB, nhưng cần thay đổi quyền production, deployment và rollback. Đây là hardening mạnh hơn dành cho wave riêng sau khi Wave 1 ổn định.

## 4. Kiến trúc Wave 1

Wave 1 giữ nguyên `Database.upsert_entity()` và `_bulk_load()` làm đường ghi chuẩn. Các thay đổi được chia thành năm đơn vị độc lập:

- `agent/config.py`: khai báo và kiểm tra cấu hình runtime production.
- `agent/database.py`: kiểm tra schema version và trigger readiness; chỉ publish cache mutation sau commit.
- `agent/entity_details.py`: dọn stale CTI, phát hiện multi-CTI và tạo cache mutation có thể stage.
- `scripts/check_migration_gate.py` và source guard tests: khóa cấu hình deployment và đường ghi source.
- Verifier mới dưới `scripts/`: đọc invariant và trả báo cáo tổng hợp.

Không tạo service mutation mới và không thêm dependency ngoài.

## 5. Cấu hình fail-closed

### 5.1. Runtime

`Settings` khai báo `ENTITY_DETAILS_TABLES` như boolean thay vì để mỗi module tự diễn giải biến môi trường. Validator thuần áp các quy tắc sau khi `ENVIRONMENT` chuẩn hóa bằng `production`:

- `DATABASE_URL` phải có scheme `postgres://` hoặc `postgresql://`.
- `ENTITY_DETAILS_TABLES` phải là `true`.
- Các khóa production hiện có vẫn tiếp tục được kiểm tra.
- Thông báo lỗi chỉ nêu tên biến hoặc loại backend; không chứa DSN hay secret.

`development` và `test` tiếp tục được phép dùng SQLite hoặc PostgreSQL disposable. Chỉ việc dùng PostgreSQL không làm môi trường bị coi là production.

### 5.2. Deployment authority

`scripts/check_migration_gate.py`, khi đọc `--environment-authority` hoặc `--environment-pin`, phải yêu cầu chính xác:

- một `ENVIRONMENT=production`;
- một `DATABASE_URL` PostgreSQL không rỗng;
- một `ENTITY_DETAILS_TABLES=true`.

Việc này đóng trường hợp VPS có `DATABASE_URL` nhưng thiếu `ENVIRONMENT`. Chế độ kiểm tra local chỉ dùng biến môi trường hiện tại không bị ép thành production nếu người vận hành không cung cấp production authority.

## 6. PostgreSQL schema và trigger readiness

Release Wave 1 phụ thuộc migration `071`, vì vậy `PG_REQUIRED_SCHEMA_VERSION` tăng lên `71`.

Thêm registry trigger bắt buộc có cấu trúc tối thiểu:

```python
PG_REQUIRED_TRIGGERS = {
    "trg_entity_ratings": "posts",
    "trg_entity_ratings_del": "posts",
}
```

Readiness truy vấn `pg_catalog.pg_trigger`, bỏ trigger internal, và xác nhận mỗi tên trigger tồn tại trên đúng bảng. Cả `_verify_pg_schema()` và `pg_schema_status()` dùng chung hàm dựng issue để tránh hai luồng có logic khác nhau.

Nếu thiếu schema, column, version hoặc trigger:

- startup PostgreSQL thất bại trước khi service được đánh dấu initialized;
- health/readiness trả `ok=false` và lý do đã redacted;
- không tự chạy migration;
- escape hatch `VL360_ALLOW_PG_SCHEMA_DRIFT` giữ hành vi hiện tại cho môi trường phát triển có chủ đích, nhưng production validator không tự bật hoặc suy diễn cờ này.

## 7. Đồng bộ CTI và cache sau commit

### 7.1. Dọn CTI

Mỗi lần `sync_entity_details()` chạy:

1. Xác định bảng CTI hợp lệ từ entity type hiện tại.
2. Xóa `entity_id` khỏi mọi bảng CTI khác.
3. Nếu type không có CTI, xóa khỏi toàn bộ bảng CTI.
4. Nếu detail rỗng, xóa hàng ở bảng hiện tại.
5. Nếu detail có dữ liệu, upsert đúng một hàng vào bảng hiện tại.

Các câu lệnh chạy trên chính connection/transaction của caller, nên thay đổi `entities`, universal columns và CTI cùng commit hoặc cùng rollback.

### 7.2. Cache mutation staging

`sync_entity_details()` và `delete_entity_details()` không sửa `_DETAIL_CACHE` ngay trong transaction. Chúng trả về một cache mutation nhỏ, bất biến, mô tả `put` hoặc `delete`.

- `upsert_entity()` áp mutation sau khi context transaction thoát thành công.
- `delete_entity()` áp mutation sau commit.
- `_bulk_load()` gom mutation và áp toàn bộ sau commit; nếu rollback thì bỏ danh sách staged.
- Nếu cache chưa được nạp, việc áp mutation là no-op như hiện tại.

Nhờ đó exception sau khi SQL CTI chạy nhưng trước commit không thể để cache đi trước database.

### 7.3. Nạp cache xác định

Danh sách bảng CTI là tuple duy nhất, có thứ tự cố định và được tái sử dụng cho sync, delete, load và verifier. `load_detail_cache()` kiểm tra duplicate `entity_id` giữa các bảng trước khi publish cache.

Nếu có multi-CTI:

- không publish cache dở dang;
- raise lỗi readiness với số lượng duplicate và tên các bảng liên quan;
- không in attributes hoặc payload của entity.

## 8. Source guard cho đường ghi entity

Thêm repository test dùng Python AST để duyệt string literal trong code runtime và scripts. Test chuẩn hóa whitespace/case rồi phát hiện SQL `INSERT INTO entities` hoặc `UPDATE entities ... attributes`.

Allowlist dùng cặp `path + function`, không allowlist cả file. Wave 1 cố định đúng inventory sau:

- các hàm ghi chuẩn trong `agent/database.py`;
- mirror universal columns trong `agent/entity_details.py` vì không ghi `attributes`;
- `_apply_universal()` trong `scripts/backfill_entity_details.py`;
- `_process_entity()` trong `scripts/cleanup_entity_jsonb.py`;
- `_apply_one_local_fix()`, `_prod_patch_one()` và `_prod_insert()` trong `scripts/sp2_reconcile.py`;
- `_apply_sqlite()` và `_apply_pg()` trong `scripts/sp6_fill_required.py`;
- `_apply_enrichment_row()` trong `scripts/import_enrichment_tips.py`;
- `apply_sqlite()` và `apply_pg()` trong `scripts/fix_tinh_moi.py`.

Các ngoại lệ script là công cụ offline/reconciliation có dry-run hoặc transaction boundary riêng; chúng được đóng băng trong Wave 1 chứ không được coi là API ghi chuẩn. Việc chuyển chúng sang entity mutation service thuộc wave sau. Không được thêm ngoại lệ mới trong Wave 1.

Mỗi ngoại lệ phải có lý do trong test. Guard chặn mọi vị trí mới và chặn việc mở rộng một ngoại lệ sang function khác. Các script runtime thông thường cần ghi entity phải gọi API `Database` thay vì tự cập nhật typed attributes.

Wave 1 không giả định regex là cơ chế bảo mật runtime; guard là regression gate giúp inventory đường ghi không tăng ngoài ý muốn.

## 9. Verifier invariant chỉ đọc

Tạo một CLI độc lập, mặc định không có chế độ sửa. CLI nhận DSN PostgreSQL từ biến môi trường giống các script hiện tại, mở transaction `READ ONLY` nếu backend hỗ trợ và không commit mutation.

Verifier báo các bộ đếm:

- tổng entity đã quét;
- entity có typed JSONB bằng cột vật lý nhưng chưa strip;
- entity có typed JSONB xung đột với cột vật lý;
- typed values không coerce được;
- entity thiếu CTI cần thiết;
- entity nằm sai CTI theo kind;
- entity nằm trong nhiều bảng CTI;
- schema version và trigger bắt buộc thiếu.

Đầu ra console và JSON chỉ gồm mã invariant, số lượng, trạng thái và metadata schema không nhạy cảm. Không xuất entity ID, tên, địa chỉ, giá trị typed, JSONB, DSN hoặc SQL chứa literal dữ liệu.

Exit code:

- `0`: tất cả invariant bắt buộc sạch;
- `1`: kết nối thành công nhưng có vi phạm;
- `2`: cấu hình, backend hoặc kết nối không hợp lệ.

Verifier dùng các hàm mapping/coercion từ `agent/entity_details.py`; không duplicate business rules. Unit test chạy trên fixture thuần; integration test chỉ chạy với PostgreSQL disposable. Không chạy trên production.

## 10. Migration 071

Tạo `agent/migrations/071_restore_entity_rating_triggers.sql` với đúng phạm vi:

1. `DROP TRIGGER IF EXISTS` rồi tạo `trg_entity_ratings` trên `posts`, chạy `AFTER INSERT OR UPDATE`, `WHEN (NEW.post_type = 'review')`.
2. `DROP TRIGGER IF EXISTS` rồi tạo `trg_entity_ratings_del` trên `posts`, chạy `AFTER DELETE`, `WHEN (OLD.post_type = 'review')`.
3. Cả hai gọi `update_entity_ratings()` đã được migration `070` sửa.
4. Ghi `schema_version(component='agent', version=71, migration='071_restore_entity_rating_triggers.sql')` theo pattern idempotent hiện có.

Migration không sửa function, không recount dữ liệu và không làm reconciliation. Logic recount thuộc `070`; `071` chỉ khôi phục wiring bị thiếu.

## 11. Xử lý lỗi và quan sát

- Lỗi cấu hình production xảy ra khi tạo `Settings`, trước khi database startup.
- Lỗi schema/trigger làm PostgreSQL initialization thất bại, không tự mutate database.
- Lỗi CTI SQL rollback toàn transaction; staged cache mutation bị bỏ.
- Lỗi multi-CTI không publish cache mới.
- Verifier bắt exception ở boundary, redacted thông báo và trả exit code `2`.
- Không log DSN, secret hoặc row payload trong các đường lỗi mới.

## 12. Kiểm thử theo TDD

### 12.1. Cấu hình

- Production hợp lệ với PostgreSQL và `ENTITY_DETAILS_TABLES=true`.
- Production thiếu DSN, dùng SQLite hoặc tắt detail tables đều thất bại.
- Development/test vẫn chấp nhận SQLite và PostgreSQL disposable.
- Deployment authority thiếu hoặc khai báo sai `ENVIRONMENT`, `DATABASE_URL`, `ENTITY_DETAILS_TABLES` đều bị migration gate từ chối.

### 12.2. Schema readiness

- Đủ version/column/trigger thì pass.
- Thiếu từng trigger hoặc trigger nằm sai bảng thì fail.
- `pg_schema_status()` và startup dùng cùng issue semantics.
- Thông báo không làm lộ DSN.

### 12.3. CTI/cache

- Tạo mới và update cùng kind.
- Đổi kind xóa stale row và chỉ còn đúng CTI mới.
- Đổi sang type không có CTI xóa mọi stale row.
- Detail rỗng xóa hàng hiện tại.
- Exception trước commit giữ cache cũ.
- Commit thành công mới áp cache mutation.
- Multi-CTI làm load thất bại xác định và không publish partial cache.

### 12.4. Source guard và verifier

- Fixture có direct typed-attributes write bị phát hiện.
- Allowlist chỉ miễn đúng path/function đã khai báo.
- Từng invariant verifier có fixture sạch và fixture lỗi.
- Console/JSON output không chứa sentinel entity ID hoặc sentinel payload.
- Exit code `0`, `1`, `2` đúng hợp đồng.

### 12.5. Migration và regression

- Migration chain kết thúc ở `071` và không có gap.
- PostgreSQL disposable xác nhận hai trigger tồn tại với đúng table/event/function.
- Trigger correctness tests chứng minh insert/update/delete review cập nhật rating đúng.
- Các expectation cố định ở `tests/test_check_migration_gate.py`, `tests/test_release_quality_gates.py` và migration tests được nâng có chủ đích từ `070` lên `071`.
- Chạy toàn bộ backend test suite và các static/release gates liên quan.

Nếu workspace không có PostgreSQL disposable khả dụng, test integration PostgreSQL được đánh dấu rõ là chưa chạy; unit/static tests vẫn phải pass. Không dùng production để lấp khoảng trống test.

## 13. Tiêu chí hoàn thành

- Test mới được viết red trước implementation và green sau implementation.
- Full suite liên quan không có regression mới.
- `git diff` chỉ chứa file Wave 1; không sửa hoặc stage thay đổi sẵn có của người dùng.
- Không có phiên SSH/VPS hoặc kết nối production phát sinh trong quá trình triển khai.
- Migration `071` chỉ tồn tại và được kiểm tra trong workspace/disposable database.
- Verifier chỉ đọc, redacted và có hợp đồng exit code ổn định.

## 14. Ngoài phạm vi và hướng nâng cấp

Không thuộc Wave 1:

- backfill 111 giá trị JSONB-only;
- strip 6.946 typed keys bằng cột;
- sửa 154 địa chỉ theo đơn vị hành chính mới;
- quyết định 8 conflict cần review hoặc 15 giá trị không coerce được;
- áp migration hoặc reconciliation lên production;
- thay đổi PostgreSQL roles/quyền ghi.

Các wave sau có thể lần lượt:

1. Tạo entity mutation service và chuyển toàn bộ script/caller khỏi SQL trực tiếp.
2. Bắt buộc writes qua PostgreSQL procedures và role giới hạn quyền.
3. Chạy verifier chỉ đọc trên production, lập snapshot và kế hoạch reconciliation có rollback.
4. Thực hiện cleanup theo batch nhỏ, có audit record và đối soát sau mỗi batch.

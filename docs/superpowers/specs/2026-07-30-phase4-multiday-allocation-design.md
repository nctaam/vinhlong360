# Phase 4 - Multi-day Itinerary Allocation and Load Balancing

> STATUS: draft for written-spec review
> Ngày: 2026-07-30
> Phạm vi: generator `generate_itinerary(...)`; kế thừa Phase 3, không thay đổi public API, saved schema hoặc frontend contract

## 1. Mục tiêu

Phase 3 đã chọn và xếp POI đồng thời trong từng ngày. Phase 4 xử lý phần còn lại của bài toán: phân bổ lại các POI đã được chọn giữa các ngày để tránh một ngày quá nặng, giảm quãng nối giữa ngày trước và ngày sau, nhưng vẫn giữ tất cả điểm đã chọn, metadata, anchor và tương thích ngược.

Phase 4 không mở rộng candidate pool và không gọi lại OSRM. Nó dùng các candidate content đã phát ra bởi Phase 3, scheduler hiện có và ma trận Haversine cục bộ. Nếu không có nghiệm an toàn tốt hơn, kết quả Phase 3 được giữ nguyên.

## 2. Phạm vi và bất biến

- Giữ nguyên chữ ký `generate_itinerary(...)`, MCP wrapper, `day_plans[*].stops[*]`, saved-itinerary schema, public optimizer endpoint và frontend contract.
- Chỉ thêm diagnostics optional dưới `day_plans[*].schedule`; consumer cũ có thể bỏ qua.
- Chỉ chạy Phase 4 khi `days >= 2` và mọi ngày có kết quả Phase 3 coordinate-aware an toàn.
- Giữ nguyên tập content POI Phase 3 đã chọn: không tự thêm candidate mới và không bỏ candidate khả thi chỉ vì đổi ngày.
- Mỗi content entity xuất hiện đúng một lần trên toàn itinerary; meal/rest anchor không bị chuyển ngày.
- Khóa POI đầu tiên của toàn chuyến và POI cuối cùng của toàn chuyến. Endpoint nội bộ của từng ngày được phép thay đổi.
- Mỗi ngày phải có ít nhất hai content POI. Số POI của một ngày chỉ được lệch tối đa một điểm so với số POI baseline của ngày đó.
- Meal/rest anchor tham gia mọi lần kiểm tra time window; synthetic origin không xuất hiện trong response.
- Không thêm Python/NPM dependency, API key, container, database table, migration, background request hoặc LLM runtime.
- Generator chỉ dùng `build_fallback_matrix(..., "driving")`; không gọi OSRM, web service hoặc paid service.
- Deadline Phase 4 là deadline chung cho toàn allocation attempt, mặc định 1.0 giây. Hết deadline phải trả incumbent hoàn chỉnh.
- Không deploy, push, migrate hoặc tuyên bố full repository suite xanh trong phase này.

## 3. Các phương án đã cân nhắc

### 3.1. Hybrid DP + adjacent-day local search - chọn

Giữ tập POI Phase 3, dùng label-setting/DP nhỏ để chọn endpoint nội bộ và lập lịch chuỗi ngày, sau đó thử các neighborhood `relocate`, `swap` và `boundary-swap` giữa hai ngày liền kề. Mỗi neighbor gọi lại feasibility oracle hiện có với cache và deadline chung.

Ưu điểm: tận dụng scheduler và diagnostics đã kiểm thử, xử lý được travel nối ngày, bounded CPU và fallback rõ. Nhược điểm: là local search có giới hạn, không bảo đảm global optimum trên mọi cách chia ngày.

### 3.2. Chỉ swap POI giữa các ngày, giữ endpoint Phase 3

Đơn giản và nhanh nhưng không thể tối ưu các POI nằm ở ranh giới ngày hoặc thay đổi điểm cuối làm origin cho ngày kế tiếp. Không đáp ứng đầy đủ mục tiêu giảm vòng xa.

### 3.3. Global assignment search độc lập

Xét toàn bộ cách phân bổ candidate rồi lập lịch lại từ đầu. Chất lượng lý thuyết cao hơn nhưng lặp lại logic Phase 3, có chi phí CPU tăng theo cấp số nhân và dễ làm thay đổi hành vi fallback. Không chọn.

## 4. Kiến trúc module

Tạo `agent/itinerary_multiday.py`, chỉ phụ thuộc thư viện chuẩn và public contracts từ `agent/itinerary_schedule.py` cùng `agent/itinerary_selection.py`. Module không import `knowledge`, FastAPI, MCP hoặc database.

Generator tiếp tục sở hữu:

1. Candidate collection và scoring.
2. Kết quả Phase 3, raw entity metadata và mapping ID -> entity.
3. Meal/rest anchor selection theo ngày.
4. Projection về stop shape cũ và diagnostics response.
5. Fallback nguyên trạng khi Phase 4 không đủ dữ liệu.

Phase 4 chạy sau khi tất cả ngày đã có `SelectionResult` Phase 3 nhưng trước khi generator project kết quả cuối thành `day_plans`. Nhờ vậy module nhận đủ candidate/anchor metadata và generator chỉ thực hiện projection một lần.

Module multi-day sở hữu:

1. Contract kiểm tra allocation đầu vào.
2. Xây route schedule theo allocation và endpoint nội bộ.
3. Label-setting/DP qua các ngày.
4. Sinh deterministic adjacent-day neighborhoods.
5. So sánh objective, cache feasibility và trả kết quả hoàn chỉnh.

## 5. Hợp đồng nội bộ

Các dataclass sau là nội bộ, không serialize trực tiếp ra public response:

```python
@dataclass(frozen=True)
class MultiDayDayInput:
    day_index: int
    candidates: tuple[SelectionCandidate, ...]
    fixed_stops: tuple[ScheduleStop, ...]
    baseline_order: tuple[str, ...]
    schedule_options: ScheduleOptions


@dataclass(frozen=True)
class MultiDayOptions:
    min_content_per_day: int = 2
    max_count_delta: int = 1
    max_iterations: int = 12
    deadline_seconds: float = 1.0
    max_labels_per_endpoint: int = 8


@dataclass(frozen=True)
class MultiDayDayResult:
    day_index: int
    content_ids: tuple[str, ...]
    ordered_ids: tuple[str, ...]
    schedule: ScheduleResult
    synthetic_origin_id: str | None
    load_minutes: float


@dataclass(frozen=True)
class MultiDayResult:
    days: tuple[MultiDayDayResult, ...]
    solver: str
    initial_load_minutes: tuple[float, ...]
    final_load_minutes: tuple[float, ...]
    max_imbalance_minutes: float
    move_count: int
    moved_in_by_day: tuple[tuple[str, ...], ...]
    moved_out_by_day: tuple[tuple[str, ...], ...]
    warnings: tuple[str, ...]


def optimize_multi_day_allocation(
    days: Sequence[MultiDayDayInput],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
) -> MultiDayResult:
    ...
```

Validation rejects duplicate content IDs, duplicate fixed-stop IDs, content/fixed ID overlap, unknown global anchors, fewer than two content POIs in an eligible day, invalid coordinates, invalid day indices, and non-finite option values.

`MultiDayDayResult.ordered_ids` chứa content và fixed-anchor IDs theo thứ tự phát ra, nhưng không chứa synthetic origin. `schedule` vẫn là kết quả nội bộ đầy đủ để tính travel/load; adapter bỏ origin placement khi project response.

## 6. Route DP và synthetic origin

### 6.1. Allocation state

Một allocation là tuple các content IDs theo ngày. Ban đầu lấy từ ordered content IDs của Phase 3. Neighborhood chỉ thay đổi ownership giữa hai ngày liền kề; tất cả content ID vẫn được giữ đúng một lần.

Global start là content ID đầu tiên của ngày đầu theo Phase 3 order. Global end là content ID cuối của ngày cuối. Hai ID này không được đưa vào neighborhood.

### 6.2. Route evaluation cho một ngày

Với mỗi day allocation và endpoint cuối ứng viên:

1. Ngày đầu dùng global start làm stop đầu tiên.
2. Ngày sau tạo `ScheduleStop` synthetic origin có visit time bằng 0 tại tọa độ endpoint cuối của ngày trước. ID synthetic là duy nhất theo `(day_index, previous_end_id)` và không được project ra response.
3. Endpoint cuối được chọn từ content của ngày; ngày cuối cùng phải dùng global end.
4. Content còn lại và fixed meal/rest stop nằm ở phần giữa, đều `required=True` để Phase 4 không làm mất candidate.
5. Tạo ma trận Haversine cục bộ cho origin/content/fixed stops và gọi `schedule_stop_order(...)`.
6. Kiểm tra hard constraints, placement coverage, overtime và endpoint order. Nếu không đạt, label bị loại.

Mỗi scheduler call nhận `deadline_seconds` bằng giá trị nhỏ hơn giữa deadline của ngày và thời gian còn lại của deadline Phase 4; không call nào được phép kéo dài quá deadline chung.

`load_minutes` là `max(placement.finish_visit_minute) - day_start_minute`. Với stop cuối, `finish_visit_minute` cũng là thời điểm departure; giá trị này đã bao gồm travel từ synthetic origin, waiting và visit. Do API hiện tại chưa có lodging anchor, các ngày sau dùng điểm cuối ngày trước làm origin xấp xỉ và ghi warning `overnight-origin-approximated`.

### 6.3. Label-setting qua ngày

DP tiến theo thứ tự ngày và carry endpoint cuối của ngày trước. Label A cùng endpoint hiện tại dominate label B khi A có `max_load` không lớn hơn, tổng load không lớn hơn, total travel không lớn hơn, backtrack không lớn hơn và có ít nhất một tiêu chí tốt hơn. Mỗi endpoint giữ tối đa `max_labels_per_endpoint` label tốt nhất theo comparator deterministic.

Cache feasibility theo fingerprint gồm day index, sorted content IDs, fixed IDs, previous endpoint ID và current endpoint ID. Cache chỉ sống trong một lần gọi `optimize_multi_day_allocation(...)`.

## 7. Adjacent-day local search

Sau khi có baseline hợp lệ, chạy tối đa `max_iterations` vòng steepest-descent deterministic:

- `relocate`: chuyển một content không bị khóa từ ngày d sang d+1 hoặc d-1.
- `swap`: đổi một content giữa hai ngày liền kề.
- `boundary-swap`: ưu tiên content đang ở vị trí cuối ngày d hoặc đầu ngày d+1 để giảm travel nối ngày.

Candidate neighborhood được sinh theo thứ tự day index, operation kind, reward giảm dần, visit time tăng dần và ID tăng dần. Không random, không seed RNG và không gọi network.

Neighbor bị loại nếu vi phạm min/max content count, di chuyển global anchor, duplicate ID, fixed anchor ownership hoặc không tạo được route cho bất kỳ label nào. Mỗi vòng chỉ nhận neighbor tốt hơn incumbent theo objective; nếu không có neighbor tốt hơn thì dừng sớm.

Mọi thay đổi endpoint của ngày d làm thay đổi origin ngày d+1, vì vậy evaluator chạy lại DP cho toàn chuỗi thay vì ghép hai lịch cũ không nhất quán. Cache giúp các allocation lặp lại không tính lại ma trận/scheduler.

## 8. Objective lexicographic

Chỉ nghiệm thỏa hard constraints mới được so sánh. Comparator theo thứ tự:

1. Giảm `max(final_load_minutes)`.
2. Giảm `max(final_load_minutes) - min(final_load_minutes)`.
3. Giảm tổng absolute deviation của load so với mean.
4. Giảm tổng travel minutes, gồm travel từ synthetic origin.
5. Giảm tổng backtrack ratio và số lần đổi area.
6. Giảm số content có owner khác baseline.
7. Tie-break bằng tuple allocation IDs, ordered IDs và endpoint IDs.

Tổng reward và tổng số content là bất biến vì Phase 4 chỉ di chuyển tập Phase 3 đã chọn. Nếu baseline đã có ngày ít hơn target do thiếu dữ liệu, Phase 4 giữ nguyên số đó và chỉ cho phép count delta trong bounds đã validate.

## 9. Diagnostics và public contract

Mỗi `day_plans[*].schedule` có thể nhận thêm object `allocation`:

```json
{
  "allocation": {
    "solver": "multiday-dp-local-search",
    "initial_load_minutes": 510.0,
    "final_load_minutes": 440.0,
    "max_imbalance_minutes": 35.0,
    "move_count": 2,
    "moved_in_ids": ["poi-a"],
    "moved_out_ids": ["poi-b"],
    "warnings": ["overnight-origin-approximated"]
  }
}
```

`moved_in_ids` và `moved_out_ids` là theo từng ngày; `move_count` và `max_imbalance_minutes` là giá trị toàn itinerary được lặp lại để mỗi day diagnostic tự giải thích được. Không thêm field ở top-level response. Stop entity, `time`, `note`, `is_meal`, `is_rest`, `total_stops` và các key schedule Phase 2B/3 giữ nguyên.

Các field `selection_solver`, `candidate_count`, `selected_count`, `total_reward` và `dropped_reasons` tiếp tục mô tả kết quả chọn của Phase 3 trước bước allocation. Phase 4 không sửa lại lịch sử quyết định chọn candidate; `schedule.allocation.moved_in_ids` và `moved_out_ids` là nguồn sự thật cho ownership cuối giữa các ngày. Các field route timing (`solver`, travel, waiting, overtime, slack, backtrack, skipped) được cập nhật từ schedule Phase 4. `area_focus` được tính lại từ content POI cuối cùng của ngày.

Solver values:

- `multiday-dp-local-search`: Phase 4 chạy và trả incumbent hợp lệ.
- `multiday-fallback`: Phase 4 không thể chạy an toàn; day plans giữ nguyên Phase 3.
- `multiday-deadline`: deadline hết sau khi có incumbent; incumbent được trả nguyên vẹn và warning `multiday-deadline-reached` được ghi.

## 10. Fallback và lỗi

1. Nếu một ngày có `selection_solver == "phase2b-fallback"`, `selected_count` không khớp số content baseline hoặc thiếu route coordinate, bỏ qua Phase 4 toàn lịch và ghi `multiday-fallback`.
2. Nếu baseline allocation không dựng được schedule đầy đủ, trả nguyên Phase 3 và warning `multiday-fallback`.
3. Nếu một neighbor không khả thi, chỉ loại neighbor; không làm hỏng incumbent.
4. Nếu deadline hết sau một nghiệm hợp lệ, trả nghiệm tốt nhất đã có và warning `multiday-deadline-reached`.
5. Nếu không có cải thiện, trả baseline với `solver: "multiday-dp-local-search"` và `move_count: 0`.
6. Chỉ bắt `ValueError`, `NoFeasibleScheduleError` và lỗi chuẩn hóa đã biết ở adapter; không bắt `BaseException` hoặc che lỗi lập trình.

Phase 3 schedule warnings vẫn được giữ nguyên. Warning Phase 4 nằm trong `schedule.allocation.warnings` để không thay đổi semantics của warning cũ.

## 11. Chi phí, giới hạn và rollout

- Không phát sinh request mạng, API key, dependency hoặc chi phí dịch vụ.
- Complexity bị giới hạn bởi tối đa 5 ngày, tối đa 20 content POI đã chọn, `max_labels_per_endpoint=8`, `max_iterations=12` và deadline chung 1.0 giây.
- Ma trận Haversine và schedule result cache chỉ sống trong một lần generator call; không thêm DB table hoặc persistent artifact.
- Phase 4 chỉ bật cho lịch mới trong generator; không tự thay đổi lịch đã lưu.
- Không thêm feature flag mới trong Phase 4; eligibility check và fallback là kill switch cục bộ. Mọi rollout flag bổ sung thuộc phạm vi riêng sau khi contract ổn định.
- Không deploy production, migrate hoặc push trong phạm vi đặc tả.

## 12. Kiểm thử

### 12.1. Unit tests cho module

- Validation duplicate ID, unknown global anchor, min/max count và invalid options.
- DP giữ global start/end, chọn endpoint nội bộ làm giảm travel nối ngày.
- Synthetic origin được tính vào load nhưng không xuất hiện trong `ordered_ids` public projection.
- Label dominance không loại nghiệm có load thấp hơn nhưng travel cao hơn nếu comparator yêu cầu giữ lại.
- `relocate`, `swap`, `boundary-swap` deterministic và không mất content.
- Meal/rest fixed stop không đổi ownership và vẫn thỏa time window.
- Deadline trả baseline/incumbent đầy đủ, không trả partial result.

### 12.2. Generator integration

- Fixture hai ngày lệch tải được cân bằng mà global start/end không đổi.
- POI ranh giới được chuyển ngày khi làm giảm max load; metadata và entity ID giữ nguyên.
- Phase 3 selection diagnostics vẫn mô tả baseline, còn allocation diagnostics và `area_focus` phản ánh ownership cuối.
- `total_stops`, số content, meal/rest và uniqueness giữ nguyên trước/sau Phase 4.
- Một ngày Phase 3 fallback làm Phase 4 fallback toàn lịch.
- One-day itinerary không chạy allocation mới và giữ diagnostics Phase 3.
- Public MCP forwarding, old schedule keys và saved-shape compatibility không đổi.

### 12.3. Regression commands

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
python -m ruff check agent/itinerary_multiday.py agent/itinerary_gen.py agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_multiday.py
git diff --check
```

Không tuyên bố full repository suite xanh nếu chỉ chạy ma trận trên.

## 13. Tiêu chí nghiệm thu

- Global start/end không đổi; endpoint nội bộ có thể đổi ngày.
- Mỗi content POI và anchor xuất hiện đúng một lần.
- Không có hard time-window/overtime violation trong fixture đầy đủ dữ liệu.
- Trên fixture lệch tải, `max(final_load_minutes)` hoặc load imbalance giảm so với baseline.
- Synthetic origin ảnh hưởng đúng tới travel/load nhưng không lọt vào response.
- Kết quả deterministic, bounded bởi deadline và không có network request.
- Nếu Phase 4 không an toàn, Phase 3 output vẫn nguyên vẹn và có warning rõ ràng.
- Public response/schema/MCP signature không thay đổi; diagnostics mới chỉ additive dưới `schedule.allocation`.
- Focused Phase 4 + Phase 3 matrix xanh; không deploy, migration, push hoặc chi phí mới.

## 14. Phân chia triển khai dự kiến

1. Contract và route evaluator trong `itinerary_multiday.py`.
2. Label-setting/DP qua các ngày và synthetic-origin projection.
3. Deterministic neighborhood generator, objective và deadline/cache.
4. Generator integration, allocation diagnostics và fallback.
5. Unit/integration/regression tests.
6. API contract/roadmap documentation, final review và local merge.

Mỗi task dùng TDD, commit riêng, task-scoped review và final whole-branch review trước khi merge.

# Phase 3 - Chọn POI và xếp tuyến đồng thời trong generator

> STATUS: draft for written-spec review
> Ngày: 2026-07-30
> Phạm vi: generator `generate_itinerary(...)`; không thay đổi public API, schema lưu lịch trình hoặc frontend

## 1. Mục tiêu

Thay bước chọn POI theo điểm số rồi mới lập lịch bằng một pipeline chọn - xếp tuyến - kiểm tra thời gian đồng thời cho từng ngày. Generator phải ưu tiên lịch khả thi, giữ các điểm bắt buộc, chọn đủ số điểm mục tiêu khi có thể, tăng tổng giá trị POI và giảm đường vòng mà không thêm dependency, request mạng, LLM runtime hoặc chi phí vận hành.

Phase 3 chỉ tối ưu trong từng ngày. Việc chuyển POI giữa các ngày, cân bằng tải nhiều ngày và anchor lưu trú thuộc Phase 4.

## 2. Bất biến và giới hạn

- Giữ nguyên chữ ký `generate_itinerary(...)` và các key hiện có trong response.
- Giữ nguyên `day_plans[*].stops[*]`, schema lịch đã lưu, MCP wrapper, public optimizer endpoint và frontend contract.
- Trường mới chỉ được thêm trong `day_plans[*].schedule` theo hướng tương thích ngược.
- Generator chỉ dùng ma trận Haversine cục bộ; không gọi OSRM, web service hoặc LLM.
- Không thêm Python/NPM dependency, API key, container, migration, bảng DB hoặc background request.
- Giữ số điểm nội dung mục tiêu hiện tại: 5 điểm cho lịch một ngày, 4 điểm/ngày cho lịch nhiều ngày.
- Giữ tối đa 20 POI trong candidate pool của một ngày sau pre-prune.
- Điểm đầu và cuối của seed day hiện tại là `required`; POI giữa là `optional`. Meal/rest anchor hợp lệ vẫn là required fixed-window stop trong lần đánh giá lịch.
- Không được phát cùng một entity ở nhiều ngày hoặc vừa là POI thường vừa là meal anchor.
- Nếu required endpoint thiếu tọa độ, không có đủ hai điểm định tuyến hoặc solver không trả nghiệm an toàn, ngày đó dùng nguyên pipeline Phase 2B và ghi warning.
- Không deploy, push, chạy migration hoặc tuyên bố full repository suite xanh trong phase này.

## 3. Các phương án đã cân nhắc

### 3.1. Wrapper chọn tuyến phía trên scheduler hiện có - chọn

Giữ `itinerary_schedule.py` là nguồn sự thật cho travel time, opening window, required stop, repair và diagnostics. Một module chọn mới tạo candidate subset, gọi scheduler như feasibility oracle có deadline chung, rồi so sánh các nghiệm bằng objective xác định.

Ưu điểm: kế thừa Phase 2B, phạm vi thay đổi nhỏ, fallback rõ và không làm public scheduler thành API reward-aware. Nhược điểm: exact search phải giới hạn ở pool nhỏ và cần cache kết quả đánh giá subset.

### 3.2. Đưa reward trực tiếp vào label-setting của scheduler

Cho chất lượng toán học tốt nhưng làm scheduler lõi phụ thuộc vào khái niệm generator reward, tăng rủi ro regression cho planner thủ công và public optimizer. Không chọn trong Phase 3.

### 3.3. Viết solver PCOPTW hoàn toàn độc lập

Tách biệt tốt nhưng lặp lại logic time window, blocked edge, travel matrix và diagnostics đã được kiểm thử. Không chọn vì chi phí bảo trì cao.

## 4. Kiến trúc

### 4.1. Module chọn mới

Tạo `agent/itinerary_selection.py`, không phụ thuộc `knowledge`, FastAPI, MCP hoặc database. Module chỉ dùng thư viện chuẩn và các public contract từ `itinerary_schedule.py`.

```python
@dataclass(frozen=True)
class SelectionCandidate:
    stop: ScheduleStop
    reward: float
    entity_type: str
    area: str
    fee_value: float | None = None


@dataclass(frozen=True)
class SelectionOptions:
    target_count: int
    exact_limit: int = 8
    beam_width: int = 32
    repair_iterations: int = 32
    deadline_seconds: float = 1.5


@dataclass(frozen=True)
class DroppedCandidate:
    stop_id: str
    reason: str


@dataclass(frozen=True)
class SelectionResult:
    schedule: ScheduleResult
    selected_ids: tuple[str, ...]
    dropped: tuple[DroppedCandidate, ...]
    candidate_count: int
    selected_count: int
    total_reward: float
    solver: str
    warnings: tuple[str, ...]


def select_and_schedule_day(
    candidates: Sequence[SelectionCandidate],
    required_ids: frozenset[str],
    fixed_stops: Sequence[ScheduleStop],
    matrix: TravelMatrix,
    schedule_options: ScheduleOptions,
    selection_options: SelectionOptions,
) -> SelectionResult:
    ...
```

`fixed_stops` chứa meal/rest anchor đã được Phase 2B chuẩn hóa. Chúng tham gia feasibility nhưng không tăng `selected_count`, `candidate_count` hoặc `total_reward` của POI nội dung.

### 4.2. Adapter trong generator

`agent/itinerary_gen.py` tiếp tục sở hữu:

- đọc và chấm điểm entity;
- xác định seed day, required endpoints và meal/rest anchors;
- chuyển candidate dictionary thành `SelectionCandidate`;
- ánh xạ `SelectionResult` về stop shape hiện tại;
- fallback về `_select_diverse(...)` + `_build_day_schedule(...)` của Phase 2B.

Không chuyển logic `knowledge` hoặc format public response vào module chọn.

## 5. Chuẩn hóa candidate và pre-prune

### 5.1. Candidate pool theo ngày

Pipeline hiện tại `_collect_candidates(...)` và `_score_entity(...)` không đổi. `_select_diverse(...)` vẫn tạo seed deterministic để:

1. xác định khu vực trọng tâm của ngày;
2. giữ điểm đầu và cuối làm required endpoints tương thích Phase 2B;
3. cung cấp fallback nguyên trạng nếu Phase 3 không chạy được.

Tất cả seed day được tạo trước khi giải ngày đầu tiên. Endpoint của mọi ngày được reserve toàn cục; endpoint tương lai không được chọn làm optional của ngày trước.

Pool Phase 3 gồm seed của ngày và các candidate chưa dùng ở ngày trước, ưu tiên cùng khu vực trọng tâm rồi theo thứ tự khu vực input. Sau khi một optional candidate được chọn cho ngày hiện tại, ID của nó bị loại khỏi các pool ngày sau. Một entity có thể xuất hiện trong nhiều pool thô nhưng chỉ được phát ở tối đa một ngày.

### 5.2. Dominance prune

Hai optional candidate chỉ được so dominance khi cùng `area` và `entity_type`. Candidate A loại candidate B khi đồng thời:

- `reward(A) >= reward(B)`;
- `visit_minutes(A) <= visit_minutes(B)`;
- fee của A không cao hơn B khi cả hai fee đều parse được;
- ít nhất một điều kiện tốt hơn nghiêm ngặt.

Candidate required không bao giờ bị dominance prune. Candidate bị loại ghi reason `dominated`.

`candidate_count` là số candidate duy nhất trong pool thô của ngày trước dominance, coordinate filtering và cap. `dropped_reasons` ghi một entry cho từng candidate trong pool thô không được chọn, nên `selected_count + len(dropped_reasons) == candidate_count`.

Sau dominance prune, giữ tối đa 20 candidate theo thứ tự:

1. required trước;
2. reward giảm dần;
3. visit time tăng dần;
4. entity ID tăng dần.

Candidate vượt cap ghi reason `candidate-cap`.

Optional candidate thiếu tọa độ hợp lệ bị loại với `coordinates-missing`. Required endpoint thiếu tọa độ kích hoạt fallback Phase 2B cho cả ngày.

## 6. Thuật toán chọn - xếp tuyến

### 6.1. Feasibility oracle

Mỗi subset được đánh giá bằng `schedule_stop_order(...)` trên:

1. required start;
2. optional content POI của subset;
3. meal/rest fixed stops;
4. required end.

Ma trận được xây một lần cho toàn pool bằng `build_fallback_matrix(..., "driving")`; khi đánh giá subset, tạo view ma trận theo ID thay vì tính lại Haversine. Mọi lần gọi scheduler dùng deadline còn lại của selection deadline chung.

Cache theo `frozenset(selected_ids)` để một subset chỉ được schedule một lần. Cache chỉ sống trong một lần gọi generator.

### 6.2. Objective lexicographic

Chỉ so sánh các nghiệm không vi phạm required stop, time window, blocked edge và day end. Thứ tự so sánh:

1. số content POI được chọn, tối đa `target_count`;
2. tổng reward;
3. diversity: nhiều `entity_type` hơn;
4. tổng travel minutes thấp hơn;
5. backtrack ratio thấp hơn;
6. minimum slack cao hơn;
7. tuple `selected_ids` và `ordered_ids` tăng dần để tie-break deterministic.

Cardinality đứng trước reward để giữ hành vi số stop hiện tại khi lịch vẫn khả thi. Solver không thêm quá `target_count` content POI dù còn thời gian.

### 6.3. Exact branch-and-bound

Khi số optional candidate không vượt `exact_limit=8`, duyệt subset theo reward giảm dần. Nhánh bị cắt nếu:

- không thể đạt cardinality của incumbent;
- upper bound reward không thể vượt incumbent cùng cardinality;
- tổng visit time tối thiểu đã vượt day window trước khi cộng travel;
- deadline chung đã hết.

Mọi subset còn khả năng cạnh tranh được gửi qua feasibility oracle. Nếu hết deadline sau khi đã có nghiệm, trả incumbent và warning `selection-deadline-reached`; nếu chưa có nghiệm, fallback Phase 2B.

### 6.4. Deterministic beam search

Khi pool lớn hơn exact limit, beam state gồm selected ID, remaining ID, reward upper bound và kết quả schedule gần nhất. Mỗi level thêm một candidate chưa dùng; frontier xếp theo objective và giữ tối đa `beam_width=32` state.

Không dùng random trong beam. Candidate expansion luôn theo `(-reward, visit_minutes, id)`.

### 6.5. Bounded destroy/repair

Sau exact hoặc beam, chạy tối đa 32 iteration deterministic:

- destroy: bỏ optional có reward-efficiency thấp nhất hoặc burden cao nhất;
- repair: thử chèn candidate bị drop theo reward giảm dần;
- swap: thay một selected optional bằng một dropped candidate;
- relocate/order repair do `schedule_stop_order(...)` thực hiện.

Chỉ nhận neighbor tốt hơn theo objective. Không dùng wall-clock randomness; thứ tự thao tác và tie-break đều theo ID. Warning `selection-repair-deadline-reached` được thêm nếu deadline hết giữa repair.

## 7. Meal/rest anchors và uniqueness

- Tất cả ID trong các content pool đã cap của mọi ngày được reserve cho bước tìm meal trước khi giải ngày đầu tiên. Quy tắc bảo thủ này ngăn một dish/product có thể trở thành content POI ở bất kỳ ngày nào bị dùng làm meal ở ngày khác.
- Candidate bị dominance hoặc candidate-cap không còn thuộc content pool đã cap nên có thể được dùng làm meal nếu nó không trùng endpoint, content đã chọn hoặc meal đã phát. Nếu meal đó được chọn, ID của nó được reserve trước khi các ngày sau được giải.
- Meal anchor chỉ dùng dish/product chưa nằm trong bất kỳ content pool được chọn hoặc emitted meal trước đó.
- Meal/rest anchor được đưa vào mọi feasibility evaluation để solver không chọn lịch content chiếm mất fixed window.
- Meal không có candidate hợp lệ vẫn ghi `meal-anchor-unavailable`; không tạo entity giả.
- Rest synthetic giữ `is_rest=True`, dùng tọa độ tuyến hợp lệ và không tính vào content selected count.
- Mỗi entity ID xuất hiện tối đa một lần trong toàn bộ `day_plans`.

## 8. Diagnostics và public contract

Các key hiện có trong `day_plans[*].schedule` được giữ nguyên. Thêm các key optional:

```json
{
  "selection_solver": "selection-exact|selection-beam|phase2b-fallback",
  "candidate_count": 14,
  "selected_count": 4,
  "total_reward": 41.5,
  "dropped_reasons": [
    {"stop_id": "poi-x", "reason": "dominated"},
    {"stop_id": "poi-y", "reason": "time-window-overflow"}
  ]
}
```

`total_stops` tiếp tục bằng tổng stop thực tế phát ra, gồm content và meal/rest như contract Phase 2B hiện tại. `selected_count` chỉ đếm content POI.

`candidate_count` đếm pool thô trước prune; `dropped_reasons` có đúng một entry cho mỗi candidate không được phát. Candidate bị loại trước solver vẫn có reason `dominated`, `candidate-cap` hoặc `coordinates-missing`; candidate qua solver nhưng không được chọn dùng một trong các reason còn lại.

Reason hợp lệ:

- `dominated`;
- `candidate-cap`;
- `coordinates-missing`;
- `time-window-overflow`;
- `unreachable-edge`;
- `lower-reward-alternative`;
- `selection-deadline`.

Không trả object, dataclass hoặc matrix nội bộ ra public response.

## 9. Fallback và lỗi

Fallback là theo từng ngày, không làm hỏng các ngày đã giải được:

1. Phase 3 selection thành công: dùng selection result.
2. Deadline có incumbent: dùng incumbent và warning.
3. Required endpoint thiếu tọa độ, matrix không hợp lệ, không có incumbent hoặc exception dự kiến: dùng seed Phase 2B của ngày và `selection-fallback`.
4. Phase 2B cũng thiếu tọa độ: giữ legacy timeline và warnings hiện có.

Không bắt `BaseException`; chỉ xử lý `ValueError`, `NoFeasibleScheduleError` và lỗi chuẩn hóa đã biết. Lỗi lập trình không được che bằng fallback im lặng.

## 10. Kiểm thử

### 10.1. Unit solver

- exact solver chọn subset có reward cao nhất trong cùng cardinality;
- điểm required không bao giờ bị drop;
- candidate bị dominance loại đúng reason;
- cardinality giảm khi day window không đủ;
- beam và repair deterministic qua nhiều lần chạy;
- meal window tham gia feasibility;
- deadline trả incumbent hoặc fallback, không trả partial invalid result;
- duplicate ID và matrix mismatch bị từ chối.

### 10.2. Generator integration

- một candidate điểm cao nhưng lệch tuyến/thời lượng dài bị thay bằng tập khả thi tốt hơn;
- response cũ không mất key hoặc stop field;
- diagnostics additive có count và dropped reason chính xác;
- `total_stops` khớp stop thực tế;
- không duplicate entity giữa ngày hoặc meal;
- thiếu tọa độ required giữ đúng Phase 2B fallback;
- MCP forwarding và chữ ký generator không đổi.

### 10.3. Regression matrix

Ma trận tập trung tối thiểu:

```powershell
python -m pytest agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
git diff --check
```

Không tuyên bố full backend suite xanh nếu chỉ chạy ma trận này.

## 11. Phân chia triển khai

1. Tạo contract, dominance prune và objective comparator trong `itinerary_selection.py`.
2. Thêm exact subset search với feasibility cache và deadline chung.
3. Thêm deterministic beam + bounded destroy/repair.
4. Tích hợp generator adapter, anchors, fallback và diagnostics.
5. Bổ sung MCP/contract documentation assertions nếu public source contract yêu cầu, nhưng không đổi MCP signature.

Mỗi task phải dùng TDD, commit riêng, task-scoped review và final whole-branch review trước khi merge.

## 12. Tiêu chí nghiệm thu

- Không vi phạm required endpoint hoặc hard time window trong fixture đầy đủ dữ liệu.
- Khi có nghiệm đủ target count, solver không trả ít content POI hơn target.
- Trong cùng cardinality, nghiệm exact không có tổng reward thấp hơn một alternative khả thi được fixture chứng minh.
- Không entity nào xuất hiện hai lần trong toàn bộ itinerary.
- Solver deterministic với cùng input và không dùng request mạng.
- Public response cũ vẫn parse được; diagnostics mới hoàn toàn additive.
- Fallback Phase 2B giữ hoạt động khi Phase 3 không đủ dữ liệu hoặc hết deadline trước incumbent.
- Focused regression matrix xanh; không deploy, migration, push hoặc chi phí mới.

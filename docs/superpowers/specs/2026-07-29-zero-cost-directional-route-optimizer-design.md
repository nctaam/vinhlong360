# Bộ tối ưu thứ tự điểm dừng có hướng, không tăng chi phí

> STATUS: active

**Ngày:** 2026-07-29  
**Phạm vi:** Đợt 1 - lõi tối ưu dùng chung, API công khai và trang tạo lịch trình thủ công  
**Ngoài phạm vi đợt 1:** tự động chọn POI cho lịch nhiều ngày, giờ mở cửa đầy đủ, dữ liệu giao thông thời gian thực, dịch vụ định tuyến trả phí

## 1. Mục tiêu

Xây một bộ tối ưu chạy cục bộ để sắp xếp tối đa 20 điểm dừng theo chiều từ điểm đầu đến điểm cuối, giảm đi lùi và độ vòng tuyến. Trang `tao-lich-trinh` cho phép người dùng bấm tối ưu, giữ cố định điểm đầu/cuối, nhận lại thứ tự tốt hơn và tự kiểm tra U-turn trên geometry OSRM hiện có.

Đợt này phải tạo ra một lõi Python độc lập để các luồng chat generator và day-plan có thể kế thừa ở các đợt sau, thay vì tiếp tục viết thuật toán riêng trong từng luồng.

## 2. Bất biến và giới hạn chi phí

- Không thêm dịch vụ trả phí, API key, container hoặc hạ tầng mới.
- Không thêm Python/NPM dependency nếu thư viện chuẩn đủ dùng.
- Không thay đổi schema và không ghi dữ liệu DB.
- Không gọi LLM trong quá trình tối ưu.
- Tiếp tục dùng endpoint OSRM hiện có; chỉ đổi yêu cầu route cuối sang `steps=true&continue_straight=true`.
- Tối ưu chỉ chạy khi người dùng bấm nút; không tăng số lần gọi OSRM nền khi họ thêm hoặc sửa ghi chú.
- Giữ giới hạn hiện tại là 20 điểm dừng.
- Giữ nguyên hành vi lưu/chia sẻ lịch trình và khả năng tự sắp xếp bằng nút lên/xuống.
- Không triển khai production trong task này.

## 3. Các phương án đã cân nhắc

### 3.1. Chỉ sắp xếp theo khoảng chiếu lên đường thẳng

Nhanh và dễ triển khai nhưng không xử lý tốt các điểm có cùng mức tiến triển, đường cong hoặc cụm POI hai bên hành lang. Phương án này chỉ phù hợp làm baseline.

### 3.2. Gọi dịch vụ Route Optimization bên ngoài

Có thể dùng ma trận đường thực nhưng tạo phụ thuộc chi phí, quota và nhà cung cấp. Phương án này mâu thuẫn trực tiếp với yêu cầu không phát sinh chi phí.

### 3.3. Solver portfolio chạy cục bộ - chọn

Chiếu điểm lên hành lang để tạo các cạnh có hướng; dùng dynamic programming chính xác cho tập nhỏ và beam search xác định cho tập lớn; sau đó cải thiện bằng local search có ràng buộc. Route cuối mới được OSRM kiểm tra U-turn. Đây là phương án cân bằng tốt nhất giữa chất lượng, tốc độ, khả năng giải thích và chi phí 0 đồng/tháng.

## 4. Kiến trúc

### 4.1. Lõi Python

Tạo `agent/itinerary_optimizer.py` không phụ thuộc FastAPI, database hoặc `knowledge`.

Các giao diện công khai:

```python
@dataclass(frozen=True)
class RouteStop:
    id: str
    coordinates: tuple[float, float]


@dataclass(frozen=True)
class OptimizeOptions:
    preserve_endpoints: bool = True
    strict_direction: bool = True
    station_tolerance: float = 0.02
    exact_limit: int = 10
    beam_width: int = 64
    blocked_edges: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True)
class OptimizeResult:
    ordered_ids: tuple[str, ...]
    distance_before_km: float
    distance_after_km: float
    backtrack_ratio: float
    solver: str
    warnings: tuple[str, ...]


def optimize_stop_order(
    stops: list[RouteStop],
    options: OptimizeOptions = OptimizeOptions(),
) -> OptimizeResult:
    ...
```

Tọa độ dùng thứ tự `[latitude, longitude]`, thống nhất với frontend hiện tại.

### 4.2. API

Thêm `POST /api/itineraries/optimize-order` trước route động `/api/itineraries/{itin_id}`.

Request:

```json
{
  "stops": [
    {"id": "a", "coordinates": [10.1, 106.1]},
    {"id": "b", "coordinates": [10.2, 106.2]}
  ],
  "preserve_endpoints": true,
  "strict_direction": true,
  "blocked_edges": [["a", "b"]]
}
```

Response:

```json
{
  "ordered_ids": ["a", "c", "b"],
  "distance_before_km": 18.4,
  "distance_after_km": 13.1,
  "saved_distance_km": 5.3,
  "backtrack_ratio": 0.0,
  "solver": "exact-dp",
  "warnings": []
}
```

Ràng buộc API:

- Từ 2 đến 20 điểm.
- ID phải khác nhau.
- Tọa độ hữu hạn, latitude trong `[-90, 90]`, longitude trong `[-180, 180]`.
- `blocked_edges` chỉ được tham chiếu ID có trong request.
- Lỗi đầu vào trả 422 theo cơ chế Pydantic/FastAPI.
- Không có cạnh khả thi trả 409 với thông báo tiếng Việt rõ ràng; không âm thầm trả thứ tự sai hướng.

### 4.3. Frontend planner

Trong `web-nuxt/pages/tao-lich-trinh.vue`:

- Thêm nút `Tối ưu tuyến` khi có ít nhất 3 điểm có tọa độ.
- Nút không tự chạy và không thay đổi lịch trình khi chỉ có 2 điểm.
- Điểm đầu và điểm cuối luôn được giữ cố định.
- Các stop thiếu tọa độ giữ nguyên vị trí tương đối và không được gửi vào solver; UI thông báo chúng chưa được tối ưu.
- Khi API thành công, sắp lại mảng `stops` theo `ordered_ids` mà không làm mất `time`, `note` hoặc metadata lưu cục bộ.
- Thông báo số km ước tính giảm được; nếu không giảm thì thông báo thứ tự hiện tại đã phù hợp.
- Nút lên/xuống vẫn tồn tại làm fallback và hỗ trợ tiếp cận.

## 5. Thuật toán

### 5.1. Chuẩn hóa và chiếu hành lang

Điểm đầu `S` và điểm cuối `T` xác định hành lang. Chuyển tọa độ sang mặt phẳng cục bộ bằng equirectangular approximation, đủ chính xác cho phạm vi tỉnh.

Với mỗi điểm `P` tính:

```text
station(P) = dot(P - S, T - S) / |T - S|^2
lateral(P) = |cross(P - S, T - S)| / |T - S|
```

`station` biểu diễn mức tiến triển từ đầu tới cuối. Hai điểm được nối bằng cạnh `i -> j` khi:

```text
station(j) + station_tolerance >= station(i)
(i, j) không nằm trong blocked_edges
```

Trong strict mode, cạnh giảm station quá tolerance bị cấm hoàn toàn. Trong non-strict mode, cạnh vẫn được phép nhưng bị phạt lớn; đợt 1 frontend chỉ dùng strict mode.

### 5.2. Hàm chi phí

Chi phí một cạnh:

```text
edge_cost = haversine_km(i, j)
          + 2.0 * backward_progress_km
          + 0.15 * lateral_escape_km
```

Điều kiện hướng là hard constraint trong strict mode; các hệ số chỉ phân xử giữa các nghiệm đều hợp lệ.

### 5.3. Solver portfolio

- Tối đa `exact_limit=10` điểm trung gian: dynamic programming bitmask trên các cạnh hợp lệ để tìm thứ tự có tổng chi phí thấp nhất.
- Từ 11 đến 18 điểm trung gian: beam search xác định, `beam_width=64`, ưu tiên trạng thái có chi phí thấp và station tiến xa.
- Sau nghiệm ban đầu: thử swap, relocate và Or-opt độ dài 2; chỉ nhận move giữ điểm đầu/cuối, không dùng blocked edge, không vi phạm station tolerance và giảm chi phí.
- Với đầu vào giống nhau, kết quả phải giống nhau; không dùng random.

Nếu không có hành trình thăm đủ các điểm bắt buộc, solver trả lỗi thay vì phá ràng buộc hướng.

### 5.4. Chỉ số backtrack

Với mỗi leg, tính phần giảm station nhân với chiều dài hành lang. Tổng phần đi lùi chia cho tổng chiều dài tuyến ước tính:

```text
backtrack_ratio = backward_progress_km / max(route_distance_km, epsilon)
```

Strict mode phải trả `backtrack_ratio` gần 0 trong sai số số thực.

## 6. Kiểm tra U-turn bằng OSRM hiện có

`web-nuxt/composables/useRouting.ts` đổi request thành:

```text
overview=full&geometries=geojson&steps=true&continue_straight=true
```

Mỗi route leg trả thêm:

```ts
hasUturn: boolean
```

`hasUturn` là true nếu bất kỳ step nào có `maneuver.type === 'uturn'`.

Sau khi người dùng tối ưu:

1. Planner nhận thứ tự từ API.
2. Cơ chế route hiện tại tự lấy geometry mới.
3. Nếu có U-turn, UI xác định cặp stop tương ứng và gọi lại optimizer một lần với cạnh đó trong `blocked_edges`.
4. Nếu lần hai vẫn có U-turn hoặc không còn nghiệm, giữ thứ tự tốt nhất hợp lệ về hướng và hiển thị cảnh báo để người dùng chỉnh thủ công.

Giới hạn một lần giải lại giúp tránh tăng tải cho OSRM demo. Không thực hiện vòng lặp vô hạn.

## 7. Xử lý dữ liệu không hoàn hảo

- Stop thiếu tọa độ không tham gia tối ưu nhưng không bị xóa.
- Stop trùng tọa độ giữ thứ tự ổn định theo đầu vào.
- Nếu điểm đầu và cuối trùng hoặc gần nhau dưới 20 mét, API trả 409 vì không xác định được hướng hành lang.
- Haversine và projection không được tạo NaN/Infinity.
- Đợt 1 không tuyên bố bảo đảm tuyệt đối không quay đầu ở POI có tọa độ gần đúng; UI chỉ báo kết quả theo dữ liệu hiện có.

## 8. Tương thích ngược

- Không đổi response hiện tại của `generate_itinerary`.
- Không đổi schema lịch trình đã lưu trong local storage hoặc backend.
- `RouteLeg.hasUturn` là trường bổ sung; các consumer cũ tiếp tục dùng `distance` và `duration`.
- Tối ưu là hành động chủ động; thứ tự cũ không tự thay đổi khi người dùng mở trang.

## 9. Kiểm thử

### 9.1. Backend unit tests

- Projection tăng dần trên hành lang và lateral distance đúng dấu trị tuyệt đối.
- Exact solver tìm thứ tự ngắn nhất trong tập cạnh hợp lệ.
- Strict mode không tạo cạnh đi lùi quá tolerance.
- Blocked edge không xuất hiện trong kết quả.
- Điểm đầu/cuối được giữ cố định.
- Trùng tọa độ cho kết quả ổn định.
- Không có nghiệm trả exception miền rõ ràng.
- Beam solver xác định và giữ `backtrack_ratio` bằng 0 trong fixture 20 điểm.

### 9.2. API tests

- Request hợp lệ trả đủ diagnostics.
- Ít hơn 2 hoặc nhiều hơn 20 stop trả 422.
- ID trùng, tọa độ sai và blocked edge lạ trả 422.
- Hành lang suy biến hoặc không có nghiệm trả 409.

### 9.3. Frontend tests

- `fetchRoute` gửi `steps=true` và `continue_straight=true`.
- Maneuver U-turn được ánh xạ vào đúng leg.
- Tối ưu reorder stop theo ID nhưng giữ toàn bộ dữ liệu stop.
- Stop thiếu tọa độ giữ vị trí tương đối.
- Retry chỉ chạy tối đa một lần và truyền đúng blocked edge.
- Không tối ưu tự động khi tải trang.

### 9.4. Regression

- Chạy test mới theo chu trình red-green.
- Chạy `agent/tests/test_cov_itinerary_gen.py` để chứng minh generator cũ không đổi.
- Chạy test liên quan `public_api` và test frontend hiện có.
- Chạy full backend suite với timeout đủ dài; ghi rõ test debt có sẵn nếu xuất hiện.
- Chạy Nuxt typecheck/build nếu cấu hình dự án cung cấp script tương ứng.

## 10. Tiêu chí nghiệm thu đợt 1

- Không có dependency hoặc dịch vụ trả phí mới.
- Nút tối ưu hoạt động với 3-20 stop có tọa độ.
- Điểm đầu/cuối không đổi.
- Strict mode không trả thứ tự có backtrack vượt tolerance.
- Route cuối nhận diện được U-turn từ OSRM steps.
- Một cạnh gây U-turn được cấm và giải lại tối đa một lần.
- Không làm mất dữ liệu stop hoặc phá lịch trình đã lưu.
- Toàn bộ test mới và regression liên quan vượt qua.

## 11. Kế thừa ở các đợt sau

Sau khi đợt 1 ổn định, cùng lõi `itinerary_optimizer.py` sẽ được mở rộng theo các spec riêng:

1. Chat generator: thêm origin/destination tùy chọn và chọn POI bằng prize-collecting directional DP.
2. Ward day-plan: thay sắp xếp theo khoảng cách tới tâm bằng hành lang theo điểm vào/ra xã.
3. Schedule propagation: giờ mở cửa, thời lượng, bữa ăn và giờ kết thúc.
4. Cache ma trận cặp POI trong DB hiện tại sau khi có phép đo chứng minh cần thiết.
5. Tái lập lịch phần còn lại khi người dùng đi trễ hoặc bỏ điểm.

Mỗi đợt phải giữ nguyên nguyên tắc không thêm dịch vụ trả phí và có fallback xác định khi router bên ngoài không sẵn sàng.

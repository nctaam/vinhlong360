# Chiến dịch trả nợ scorecard backend — 47 vi phạm R20.8 → ≤2

> STATUS: active
> Ngày lập: 2026-08-29. Nguồn: hồ sơ đo-trước 10-agent (workflow backend-debt-dossier),
> tổng hợp từ docs/2026-08-21-danh-gia-toan-du-an.md mục scorecard 99→81.
> Lệnh chủ dự án "tiếp tục thực hiện dự án" 2026-08-29 = lệnh xếp lịch dự án trả nợ này.
> Kỷ luật: B3 (test trước vùng mù — GĐ C/E có commit test-only riêng), B5 (1 lát = 1 commit,
> hệ xanh sau mỗi lát), đo scorecard bằng --no-append (KHÔNG ghi history khi chưa kết đợt).

# Danh sách lát thi công — chiến dịch trả nợ R20.8 (47 vi phạm → ≤2)

## Quy ước chung (áp mọi lát)

- **1 lát = 1 commit**, hệ thống xanh sau mỗi lát (B5). Helper luôn **ở CÙNG file** trừ khi lát ghi khác — né nghĩa vụ ghép test R20.7 mới và mìn `router` R20.9.
- **Verify chuẩn:** `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest <đích> -q --tb=line` rồi `python scripts/scorecard.py` (điểm không tụt, nợ R20.8 giảm).
- **Nhóm cần PG** (cases, prefs-PG, personalization, database): thêm `$env:VL360_TEST_DATABASE_URL='postgresql://vl360:vl360@127.0.0.1:5433/<db>'` và chạy **TRƯỚC + SAU** lát — không có container thì test skip, "xanh" là mù.
- Chuỗi tiếng Việt/SSE/ASCII-không-dấu: **giữ nguyên từng byte**, sửa bằng Edit tool, tránh bash heredoc (bẫy nuốt backslash + NFD chữ "đ").
- Test so-chuỗi-nguồn (getsource/marker) bị vỡ do dời code: **sửa cùng commit, đổi đích soi, không xoá assert**.
- GĐ 0 trước khi bắt đầu: đo baseline full-suite (đối chiếu 16 fail-đã-biết ROADMAP), bật container PG, **cây + máy đứng yên** (không dev server dùng chung DB).

---

## GĐ A — Thấp: hàm thuần, phủ dày (mổ ngay)

| # | Lát (file — hàm) | Làm trước | Verify (đích) |
|---|---|---|---|
| 1 | `agent/trust_policy.py` — `_safe_region_label`, `build_explanation` | không | `test_trust_policy.py` |
| 2 | `agent/location_resolver.py` — `contains_raw_location_value`, `_contains_gps_echo` | không. **KHÔNG hợp nhất detector với trust_policy** (khác `math.isfinite` có chủ đích) | `test_location_resolver.py` + PG `test_location_remediation_postgres.py` |
| 3 | `agent/auth_middleware.py` — `verify_user_bound_token` | tuỳ chọn: đắp test nhánh chưa phủ (token>2048, đếm `.`, base64 phi-canonical). Pairing qua import sẵn có — **đừng đổi thành importorskip** | `test_location_resolver.py test_user_preferences.py` |
| 4 | `agent/config.py` — `validate_production_keys` | không. Message lỗi là hợp đồng; không nhét secret/DSN vào message | `tests/test_config.py` + `agent/tests/test_case_policy.py` |
| 5 | `agent/user_preferences.py` — `normalize_preference_patch`, `_authorize_region_patch`, `invalid_region_reason` | không. **KHÔNG xê dịch khối regex SQL dòng 461-509** | `test_user_preferences.py test_location_resolver.py` |
| 6 | `agent/public_api.py` — `_apply_events_to_profile`, `_score_interest_hits` | không. Giữ chống-đếm-đôi `fallback['interest_keys']=[]`; chuỗi 'Khớp sở thích ẩm thực' byte-identical | `test_trust_policy.py test_media_policy.py` + PG `test_personalization_events.py` |
| 7 | `agent/cases/audit.py` — `canonical_case_projection`, `__post_init__ CaseAuditDraft` | không. Giữ `type(x) is not str`; helper không set thuộc tính (frozen) | `test_case_audit.py test_case_store.py` + PG `test_case_transaction_postgres.py` |
| 8 | `agent/cases/correction.py` — `validate_decision`, `validate_change_set` | không. Giữ thứ tự reject (mã lỗi đầu tiên là hợp đồng) | `test_correction_decisions.py test_correction_changesets.py` + PG |
| 9 | `agent/cases/policy.py` — `_validate_coverage`, `load_case_policy` | đắp 2-3 case reject (timezone/hours rỗng). **Không nới hằng `correction-pilot-v1`** | `test_case_policy.py` |
| 10 | `agent/gpt55_quality_burst.py` — `validate_candidate_record`, `enforce_apply_policy` | không. Giữ thứ tự append errors + thứ tự elif (confidence-reject thắng); **chỉ mổ code, không chạy /admin/apply (B7)** | `tests/test_gpt55_quality_burst.py` |

## GĐ B — Vừa: có mìn so-chuỗi / PG-gated / cần đắp test

| # | Lát | Làm trước | Verify |
|---|---|---|---|
| 11 | `agent/cases/service.py` — `_validate_items` | không. **Đừng lan sang `create_correction`** (test_case_service.py:370-392 so-chuỗi + khoá signature); không đụng `_URGENT_EXACT/_FOLDED` | `test_correction_create.py test_case_service.py` + PG |
| 12 | `agent/user_preferences.py` — `_patch_preferences_in_connection` | không. Helper không mở connection mới; giữ thứ tự authorize→load→quarantine→merge→…→write | PG round-trip + route: `test_user_preferences.py` (chạy nhóm PG trước & sau) |
| 13 | `agent/public_api.py` — `_load_user_signal_entities` | không. **GIỮ 2 chuỗi SQL trong thân** (test_qa_fixes.py:546 so-chuỗi); nếu buộc dời → sửa test cùng commit | `test_qa_fixes.py` + PG `test_personalization_events.py` |
| 14 | `agent/personalization_events.py` — `purge_legacy_events` | không. Khối atomic-write (os.replace/fsync) giữ **nguyên byte từng call** — đúng lớp lỗi Windows-dev/Linux-prod §5b; đường erasure là nghĩa vụ pháp lý | `test_personalization_events.py` |
| 15 | `agent/database.py` — `_pg_schema_snapshot` | **Sửa test_database.py:126 (getsource 10 mảnh SQL) cùng commit**, SQL nguyên văn, giữ guard `hasattr(cur,'tables')` | PG `test_migration_readiness_postgres.py test_pg_schema_readiness.py` + **§5b:** `python -m pytest tests/launch_safety/ -m "" -n0` |
| 16 | `agent/server.py` — `readiness_probe` | không. **Giữ nguyên trong thân:** `"privacy_boundary": privacy_boundary_readiness()` + `asyncio.to_thread` (3 test so-chuỗi canh); **cấm biến module `router`**; giữ shape JSON (LB probe prod) | `test_case_schema_postgres.py test_gap_fixes.py test_session_be.py test_privacy_source_guards.py tests/test_integration.py` |
| 17 | `gpt55` — **commit test-only (B3)**: characterization cho `relationship_targets` (include/reasons), `candidate_places_for_entity` (bảng chấm điểm), `heuristic_quality_status` (bảng chân trị), nhánh thêm `placeid_candidate_from_decision` | — | `tests/test_gpt55_quality_burst.py` |
| 18 | `gpt55` — `relationship_targets`, `build_manifest` | lát 17 xong. Seq shard phụ thuộc `shards` dùng chung — helper nhận vào, không reset | như trên |
| 19 | `gpt55` — `candidate_places_for_entity`, `placeid_candidate_from_decision` | lát 17 xong. Giữ nguyên byte `conflict_reason` | như trên |
| 20 | `gpt55` — `heuristic_quality_status`, `generate_heuristic_eval_cases` | lát 17 xong. **Chuỗi query ASCII không dấu — tuyệt đối không chuẩn hoá thành có dấu** | như trên |

## GĐ C — CAO: 0 phủ hành vi hoặc chỉ so-chuỗi — B3 BẮT BUỘC, test trước trong commit riêng

**CẢNH BÁO RIÊNG nhóm "cao":** 6 hàm dưới đây hoặc không có test hành vi nào, hoặc chỉ được "canh gác" bằng test so-chuỗi-nguồn. Mổ khi chưa đắp test = refactor mù vùng side-effect (mạng/LLM/DB/file). Tuyệt đối không gộp bước đắp-test và bước mổ vào một commit.

| # | Lát | Làm trước | Verify |
|---|---|---|---|
| 21 | `agent/learn_loop.py` — **commit test hành vi** cho `_persist_backfilled_coords` (khuôn `test_persist_new_entities_preserves_concurrent_fields`: tmp data.json + fake sys.modules; assert ghi `coordinates` không ghi `coords`, dual-write DB, reload). **Test không được chạm DATA_JSON/DB thật (B1)** | — | `test_learn_loop.py` |
| 22 | `learn_loop` — mổ `_persist_backfilled_coords` (3 helper) | lát 21. **Viết lại test so-chuỗi :195-203 CÙNG commit** (soi helper hoặc chuyển hẳn sang hành vi) | `test_learn_loop.py` |
| 23 | `gpt55` — **commit test (B3)** cho 3 hàm cao: `source_candidate_for_entity` (llm giả 4 nhánh, `no_web=True`, monkeypatch `search_web` — **đừng import DDGS thật**), `audit_accuracy_chunk`, `audit_relationship_chunk` (llm giả 3 nhánh mỗi hàm) | — | `tests/test_gpt55_quality_burst.py` |
| 24 | `gpt55` — mổ `source_candidate_for_entity`, `audit_accuracy_chunk`, `audit_relationship_chunk` | lát 23. Giữ nguyên `int(item.get('relationship_index'))` có thể ném — không "sửa tiện tay" | như trên |

## GĐ D — Itinerary (vừa/vua nhưng dây nhợ monkeypatch dày — sau khi đã quen tay)

| # | Lát | Làm trước | Verify |
|---|---|---|---|
| 25 | `agent/itineraries/itinerary_multiday.py` — `__post_init__ (MultiDayOptions)`, `_validate_inputs` | đắp test nhánh raise chưa phủ (rẻ, hàm thuần). **Đừng đụng `__post_init__` dòng 38** (ngoài phạm vi) | `test_itinerary_multiday.py` |
| 26 | multiday — `_solve_allocation`, `_generate_neighbors` | characterization test nhánh `_routed_boundary_id` (day_results khác rỗng) TRƯỚC. **GIỮ TÊN `_solve_allocation`** (API ngầm của monkeypatch + fallback) | `test_itinerary_multiday.py` |
| 27 | multiday — `_schedule_day` | không. **BẤT BIẾN: đúng 2 lời gọi `time.perf_counter`** (iterator 2 tick trong test); mọi lời gọi time/schedule_stop_order qua tên module-level | `test_itinerary_multiday.py test_itinerary_generator_schedule.py` |
| 28 | multiday — `optimize_multi_day_allocation` | không. Helper gọi `_solve_allocation`/`_local_search_deadline_reached`/`_generate_neighbors` bằng **tên trần cấp module** (2 test monkeypatch); giữ nguyên văn solver string | `test_itinerary_multiday.py test_itinerary_generator_multiday.py` |
| 29 | `agent/itineraries/itinerary_gen.py` — `_build_joint_day_plans` (5 helper, đúng 11 stage plan `docs/superpowers/plans/2026-07-30-phase4-multiday-allocation.md:859-871`) | không (phủ gián tiếp ~50 test đủ dày). 3 tập id xuyên ngày truyền vào + cập nhật đúng thứ tự; chỉ bắt `(NoFeasibleScheduleError, ValueError)`. **Ghi gỡ DEFER 2 + cập nhật cx 24→37 vào 90-exceptions-log cùng commit** | trọn bộ regression Step 4 của plan (9 file test, lệnh ở plan :904) |
| 30 | itin-gen — `_candidate_fee_value` | **CHẶN: DEFER 3 — phải có chủ dự án gật trước khi mổ (§4)**. Nếu không gật → để lại, tính là 1 trong ≤2 nợ cho phép | `test_itinerary_gen_fee_coverage.py test_itinerary_gen_day_plans.py` |
| 31 | `agent/itineraries/itinerary_selection.py` — **commit test pin (B3)**: 'lower-reward-alternative' + 'selection-repair-deadline-reached' + đắp thêm nhánh beam/repair | — | `test_itinerary_selection.py` |
| 32 | selection — mổ `select_and_schedule_day` bằng **closure LỒNG trong cùng hàm/cùng file** (KHÔNG module-level — comment :290 cấm; checker đếm nested riêng nên đủ hạ cx) | lát 31. **Không thêm/bớt lời gọi `perf_counter`** (đồng hồ đếm-mỗi-lần-đọc); không "dọn cho nhất quán" 2 quả mìn pin sẵn (:448,:467) | `test_itinerary_selection.py test_itinerary_generator_selection.py test_itinerary_generator_schedule.py` |

## GĐ E — Chat giants (CUỐI CÙNG, sau khi mọi khuôn đã ổn định)

Mọi helper tách **ra module-level trong chính `agent/chat/api.py`** (ast.walk — helper lồng không giảm cx cha; mở module mới = thêm nghĩa vụ R20.7 + mìn `router`).

| # | Lát | Làm trước | Verify |
|---|---|---|---|
| 33 | **commit test-only (B3)**: đắp test hành vi khối KB-fallback (dòng 2104-2204, hiện ~3-4 test) + nhánh privacy-mid-stream của `_event_stream_body` | — | `test_chat_tools.py test_chat_privacy_transport.py` + test mới |
| 34 | `chat()` phần THUẦN: `_is_error_reply`, `_kb_clean_query`, `_detect_month`, `_format_kb_reply`, `_kb_fallback_search`, `_compose_enriched_system` (dùng chung với stream), `_pick_delivery_model` | lát 33. Chuỗi dòng 2172 chứa 'Bến Tre, Trà Vinh' — **byte-identical** (check_tinh_cu + NFD) | `test_chat_smoke.py test_chat_usage_accounting.py test_chat_owner_boundary.py test_chat_api_boundary.py` |
| 35 | `chat()` phần SINK: `_try_semantic_cache_hit`/`_try_exact_cache_hit`, `_record_chat_outcome`, `_maybe_cache_reply` | **Sửa `test_privacy_source_guards.py` (13 sink + marker AST-domination) + `test_chat_api_boundary.py:60` CÙNG commit** — rào đi theo helper, giữ yêu cầu marker-dominate + tail-order sink-sau-marker; lease contextvar không đẩy sang thread khác context | `test_privacy_source_guards.py test_chat_privacy_transport.py test_chat_accounting_owner.py tests/test_integration.py` |
| 36 | `chat_stream()`: `_event_stream_body` ra module-level (`StreamContext` dataclass thay nonlocal), `_cached_stream_gen`, `_stream_privacy_guard`, `_try_stream_cache_hits`, `_pick_stream_model` | **Sửa 2 test getsource `test_chat_stream_sse.py:90-105` CÙNG commit** (đổi đích soi, không xoá assert); server.py re-export — không đổi tên/chữ ký `chat_stream` | `test_chat_stream_sse.py` (26 test) + owner_boundary + privacy_transport |
| 37 | `_event_stream_body` mổ sâu: `_pump_llm_tokens` (khử 2 khối trùng ~40 cx), `_emit_decision_failure_frames`, `_run_stream_tool_round`, `_deliver_safe_stream_reply`, `_record_stream_outcome`, `_synthesize_after_rounds` | lát 33+36. **Thứ tự cancellation bất khả xâm phạm:** CancelledError/GeneratorExit → `_cancelled.set()` → await producer → add_response (6 test ghim); mở rộng rào privacy soi helper mới (marker riêng trước sink) | `test_chat_stream_sse.py` đủ 26 + `test_chat_history_continuity.py` |

**CẢNH BÁO "cao" của GĐ E:** `chat_stream()` và `_event_stream_body()` xếp cao vì hành vi bị ghim bằng getsource + rào AST — mọi lần dời code là đỏ-giả hàng loạt; kỷ luật là *sửa-rào-cùng-commit*, không bao giờ nới rào.

## Khép chiến dịch

1. Full suite: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q --tb=line` (máy đứng yên) — đối chiếu đúng **16 fail-đã-biết** ROADMAP, 0 fail mới.
2. `python scripts/scorecard.py` — nợ R20.8 ≤ 2 (dự kiến: `_candidate_fee_value` nếu chủ chưa gật + 1 dự phòng).
3. `pre_merge_check` xanh; cập nhật `baseline.json` ratchet xuống + giải trình **trong cùng commit**; cập nhật `docs/standards/90-exceptions-log.md` (gỡ DEFER 2, trạng thái DEFER 3, số cx mới).
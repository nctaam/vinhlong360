# Nhật ký ngoại lệ & SKIP — vinhlong360
> **STATUS (2026-07-07): active — file máy-ghi (COMMITTED, không gitignore).**

## Ngoại lệ rule đã ký (chủ dự án)
- 2026-07-07 · R30.5 season-ring 22px (hình học — đo thực nghiệm 11/12 tap sai khi nới 44px); month-grid = fallback a11y.
- 2026-07-07 · R40.4 hero Ken Burns + parallax homepage — signature, có prefers-reduced-motion.
- 2026-07-07 · R40.5 top-nav + hamburger là chuẩn điều hướng đã chọn (không bottom-nav).
- 2026-07-07 · R10.5, R20.6, R30.4, R50.6, R70.2, R70.5 — dạng checklist/quy-trình (không máy-đo trọn vẹn).
- 2026-07-10 · **R20.8 = 12 (server.py chat-handler) DEFER có-lý-do** (soft-ratchet, baseline giữ 12). 90/102 offender runtime+script đã refactor ≤12 (batch-1/2/3 + workflow, full-pytest 0-regression). 12 hàm còn lại (chat cx111, chat_stream 97, event_stream 62, _build_messages 45, _call_tool_impl 131 + 7 hàm nhỏ) là **VÙNG-MÙ §B3** (chat-handler = lõi sản phẩm, phải có test-phủ TRƯỚC khi sửa). Thử refactor 1 agent (2026-07-10): tách _call_tool_impl→per-tool helper NHƯNG **làm vỡ hành vi thật** (test_weather_tool_uses_circuit_breaker: pass→fail — thay đổi circuit-breaker wrapping), helper vẫn cx23-26, +2 offender. **Đã revert.** Kết luận: pipeline state-heavy = complexity BẢN CHẤT; ép ≤12 = helper-soup + rủi ro threading, phá lõi cho một chỉ số nội-bộ. Mở lại KHI có bộ test tích hợp chat/tool/stream đủ (mock LLM+tool) — task riêng, không grind mù.

## SKIP-log (tự động ghi bởi run_hard khi SKIP_CHECKS hợp lệ)

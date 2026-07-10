# Nhật ký ngoại lệ & SKIP — vinhlong360
> **STATUS (2026-07-07): active — file máy-ghi (COMMITTED, không gitignore).**

## Ngoại lệ rule đã ký (chủ dự án)
- 2026-07-07 · R30.5 season-ring 22px (hình học — đo thực nghiệm 11/12 tap sai khi nới 44px); month-grid = fallback a11y.
- 2026-07-07 · R40.4 hero Ken Burns + parallax homepage — signature, có prefers-reduced-motion.
- 2026-07-07 · R40.5 top-nav + hamburger là chuẩn điều hướng đã chọn (không bottom-nav).
- 2026-07-07 · R10.5, R20.6, R30.4, R50.6, R70.2, R70.5 — dạng checklist/quy-trình (không máy-đo trọn vẹn).
- 2026-07-10 · **R20.8 = 12 (server.py chat-handler) DEFER có-lý-do** (soft-ratchet, baseline giữ 12). 90/102 offender runtime+script đã refactor ≤12 (batch-1/2/3 + workflow, full-pytest 0-regression). 12 hàm còn lại (chat cx111, chat_stream 97, event_stream 62, _build_messages 45, _call_tool_impl 131 + 7 hàm nhỏ) là **VÙNG-MÙ §B3** (chat-handler = lõi sản phẩm, phải có test-phủ TRƯỚC khi sửa). Thử refactor 1 agent (2026-07-10): tách _call_tool_impl→per-tool helper NHƯNG **làm vỡ hành vi thật** (test_weather_tool_uses_circuit_breaker: pass→fail — thay đổi circuit-breaker wrapping), helper vẫn cx23-26, +2 offender. **Đã revert.** Kết luận: pipeline state-heavy = complexity BẢN CHẤT; ép ≤12 = helper-soup + rủi ro threading, phá lõi cho một chỉ số nội-bộ. Mở lại KHI có bộ test tích hợp chat/tool/stream đủ (mock LLM+tool) — task riêng, không grind mù.

## Floor legitimate (baseline không-nên-về-0 — đã trả hết phần mechanical)
- 2026-07-10 · **R30.3 fe_colors floor = 309** (từ 1373). Đã trả: 482 false-positive token-rgba, 67 hex→token, 450 overlay trắng/đen→primitive, 16 systemGray→primitive, 158 dead hex-fallback. 309 CÒN LẠI = ~185 màu trong **SVG presentation-attribute** (fill=/stroke=/stop-color= của illustration Hero/Avatar/UserCover — SVG-attr KHÔNG resolve `var()`, phải literal) + ~124 **one-off/decorative** (#74abb5×52 màu trang trí, one-off khớp token .dark-override = cấm thay). Tokenize artwork = sai ngữ nghĩa; token cho one-off = token-bloat. Floor hợp lệ.
- 2026-07-10 · **R30.2 emoji floor = 626 grandfathered-legitimate.** Phân tích: 550 **string-context** (SEO meta / map label / select option trong `<script>` — emoji ĐÚNG chỗ, đổi = vỡ SEO/nhãn) + ~98 **decorative-editorial** (hero-glyph `aria-hidden` 🏛️🎋🏅, marker động 👤/📍 — thiết-kế cinematic-editorial CHỦ ĐÍCH) + phần functional ✕✓☰ rải rác admin nội-bộ (nhiều cái CSS `content:` không convert IconLine được). Soft-ratchet đã phục vụ đúng: chặn emoji functional MỚI. Ép giảm = degrade design + rủi-ro regression cho chỉ-số nội-bộ. Floor hợp lệ.

## SKIP-log (tự động ghi bởi run_hard khi SKIP_CHECKS hợp lệ)

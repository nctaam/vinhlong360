"""
Smoke test integration cho /chat (GĐ1.3).

Mock LLM (không gọi mạng) để bọc luồng chat handler end-to-end:
request -> _build_messages -> agent loop -> ChatResponse. Đây là lưới an toàn
cho các refactor GĐ3 (DB-as-SoT) và GĐ4 (concurrency).

Marked `integration` -> không chạy trong unit baseline mặc định, có chạy ở CI.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Env phải set TRƯỚC khi import server (đọc lúc import + lifespan startup).
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("DESTRUCTIVE_OPS_LOCKED", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402


def _fake_completion(content="Vĩnh Long có Văn Thánh Miếu và làng gốm Mang Thít để tham quan."):
    """Giả lập completion KHÔNG gọi tool -> agent loop trả lời thẳng."""
    msg = SimpleNamespace(content=content, tool_calls=None, role="assistant", function_call=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=120, completion_tokens=25, total_tokens=145)
    return SimpleNamespace(choices=[choice], usage=usage, model="test-model", id="cmpl-test")


@pytest.fixture
def client_mocked():
    # Patch tại client module-global của server: cả circuit-breaker và orchestrated
    # đều gọi server.client.chat.completions.create.
    with patch.object(server.client.chat.completions, "create",
                      side_effect=lambda *a, **k: _fake_completion()):
        with TestClient(server.app) as c:
            yield c


def test_chat_returns_200_and_reply(client_mocked):
    r = client_mocked.post("/chat", json={"message": "Vĩnh Long có gì chơi?", "session_id": "smoke1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("reply"), str)
    assert body["reply"].strip(), "reply không được rỗng"


def test_chat_rejects_empty_message(client_mocked):
    r = client_mocked.post("/chat", json={"message": ""})
    assert r.status_code == 422  # pydantic min_length=1


def test_health_is_ok(client_mocked):
    r = client_mocked.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "degraded")


def test_admin_edit_reflects_in_chat_and_api(client_mocked):
    """GĐ3.6 / DoD-3: sửa entity ở admin -> CẢ chat (knowledge in-memory) lẫn /api thấy ngay.

    Đây là bằng chứng split-brain đã được gỡ (một nguồn = DB). Self-cleaning.
    """
    import knowledge  # cùng module singleton server đang dùng
    from middleware import ADMIN_API_KEY as _ADMIN_KEY  # đúng key app đang dùng

    eid = "test-gd3-splitbrain-entity"
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    client_mocked.delete(f"/admin/entities/{eid}", headers=hdr)  # dọn tồn dư
    try:
        r = client_mocked.post("/admin/entities", headers=hdr, json={
            "id": eid, "type": "dish", "name": "Món test GĐ3", "summary": "SENTINEL_GD3"})
        assert r.status_code == 200, r.text

        # /api đọc DB -> thấy
        r2 = client_mocked.get(f"/api/entities/{eid}")
        assert r2.status_code == 200, r2.text
        assert r2.json().get("name") == "Món test GĐ3"

        # chat source (knowledge in-memory, reload qua _sync_kb) -> thấy
        assert eid in knowledge._entities
        assert knowledge._entities[eid]["name"] == "Món test GĐ3"
    finally:
        client_mocked.delete(f"/admin/entities/{eid}", headers=hdr)

    # xoá cũng write-through: chat không còn thấy
    assert eid not in knowledge._entities


def test_ugc_degrades_to_503_on_sqlite(client_mocked):
    """GĐ3.1 (quyết định): UGC/auth Postgres-only — trên SQLite dev trả 503 rõ ràng (không crash 500)."""
    r = client_mocked.post("/auth/request-otp", json={"phone": "0912345678"})
    assert r.status_code == 503, r.text


def test_facilities_endpoint_wired(client_mocked):
    """GĐ13.4: /api/facilities trả {facilities:[...]} (rỗng khi chưa có dữ liệu danh bạ)."""
    r = client_mocked.get("/api/facilities")
    assert r.status_code == 200, r.text
    assert isinstance(r.json().get("facilities"), list)


def test_cost_endpoints_require_admin(client_mocked):
    """GĐ4.2: /image/recognize (LLM vision) + /vectors/build (rebuild nặng) chặn ẩn danh."""
    assert client_mocked.post("/image/recognize", json={"image": "x"}).status_code == 401
    assert client_mocked.post("/vectors/build").status_code == 401


def test_reload_requires_admin_and_reads_db(client_mocked):
    """GĐ3.8: /reload an toàn (nạp từ DB) nhưng yêu cầu admin."""
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    assert client_mocked.post("/reload").status_code == 401  # ẩn danh bị chặn
    r = client_mocked.post("/reload", headers={"X-Admin-Key": _ADMIN_KEY})
    assert r.status_code == 200, r.text
    assert r.json().get("source") == "db"


def test_entity_image_management(client_mocked):
    """Feature: quản lý ảnh entity — add (validate URL) + remove theo index."""
    from database import db
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    eid = "img-test-ent"
    try:
        db.upsert_entity({"id": eid, "type": "attraction", "name": "Ảnh test"})
        # URL sai -> 400
        assert client_mocked.post(f"/admin/entities/{eid}/images", headers=hdr, json={"url": "ftp://x"}).status_code == 400
        # add hợp lệ
        r = client_mocked.post(f"/admin/entities/{eid}/images", headers=hdr, json={"url": "https://ex.com/a.jpg"})
        assert r.status_code == 200 and "https://ex.com/a.jpg" in r.json()["images"]
        # remove index 0
        d = client_mocked.delete(f"/admin/entities/{eid}/images/0", headers=hdr)
        assert d.status_code == 200 and "https://ex.com/a.jpg" not in d.json().get("images", [])
    finally:
        db.delete_entity(eid)


def test_bulk_operations(client_mocked):
    """Feature: thao tác hàng loạt — bulk-delete + bulk-update-confidence."""
    from database import db
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    ids = ["bulk-a", "bulk-b"]
    try:
        for i in ids:
            db.upsert_entity({"id": i, "type": "dish", "name": f"Bulk {i}", "confidence": 0.5})
        # bulk confidence
        r = client_mocked.post("/admin/entities/bulk-update-confidence?confidence=0.9", headers=hdr, json=ids)
        assert r.status_code == 200 and r.json()["count"] == 2
        assert db.get_entity("bulk-a")["confidence"] == 0.9
        # bulk delete
        r2 = client_mocked.post("/admin/entities/bulk-delete", headers=hdr, json=ids)
        assert r2.status_code == 200 and r2.json()["count"] == 2
        assert db.get_entity("bulk-a") is None
    finally:
        for i in ids:
            db.delete_entity(i)


def test_cost_overview_endpoint(client_mocked):
    """Feature: bảng chi phí — /admin/cost-overview trả llm + agent_budget; auth-gated."""
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    assert client_mocked.get("/admin/cost-overview").status_code == 401
    r = client_mocked.get("/admin/cost-overview", headers={"X-Admin-Key": _ADMIN_KEY})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "llm" in body and "agent_budget" in body
    assert "enabled" in body["agent_budget"]  # off mặc định


def test_info_report_resolve_action(client_mocked, tmp_path, monkeypatch):
    """Feature: hàng đợi báo-sai có action — resolve đổi status trong reports.jsonl."""
    import public_api
    import admin as admin_mod
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    rfile = tmp_path / "reports.jsonl"
    monkeypatch.setattr(public_api, "REPORTS_FILE", rfile)
    monkeypatch.setattr(admin_mod, "_INFO_REPORTS_FILE", rfile)
    hdr = {"X-Admin-Key": _ADMIN_KEY}

    # tạo 1 báo-sai
    client_mocked.post("/api/report", json={"target_id": "x1", "target_type": "facility", "reason": "sai sđt"})
    lst = client_mocked.get("/admin/info-reports", headers=hdr).json()
    assert lst["open"] == 1
    ts = lst["reports"][0]["ts"]

    # resolve
    r = client_mocked.post("/admin/info-reports/action", headers=hdr, json={"ts": ts, "status": "resolved"})
    assert r.status_code == 200, r.text
    after = client_mocked.get("/admin/info-reports", headers=hdr).json()
    assert after["open"] == 0
    assert after["reports"][0]["status"] == "resolved"

    # ts không tồn tại -> 404
    assert client_mocked.post("/admin/info-reports/action", headers=hdr,
                              json={"ts": "khong-co", "status": "open"}).status_code == 404


def test_create_facility_keeps_official_source(client_mocked):
    """Feature danh bạ: tạo facility giữ NGUỒN chính thống (không bị ghi đè 'admin') + vào /api/facilities."""
    from database import db
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    eid = "ubnd-test-danhba"
    try:
        r = client_mocked.post("/admin/entities", headers=hdr, json={
            "id": eid, "type": "facility", "name": "UBND xã Test Danh Bạ", "placeId": "xa-x",
            "attributes": {"office_kind": "ubnd", "phone": "0270 111 222", "address": "Ấp 1"},
            "source": {"url": "https://vinhlong.gov.vn", "title": "cổng tỉnh"}})
        assert r.status_code == 200, r.text
        got = db.get_entity(eid)
        assert got["source"].get("url") == "https://vinhlong.gov.vn"   # KHÔNG bị ghi đè 'admin'
        assert got["attributes"]["office_kind"] == "ubnd"
    finally:
        db.delete_entity(eid)


def test_assign_place_to_unclassified(client_mocked):
    """Feature: gán xã cho entity chưa phân loại — list unclassified + assign + validate."""
    from database import db
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    seeded = ["xa-assign-test", "ent-unclass-1"]
    try:
        db.upsert_entity({"id": "xa-assign-test", "type": "place", "name": "Xã Assign Test",
                          "area": "vinh-long", "level": "xa"})
        db.upsert_entity({"id": "ent-unclass-1", "type": "attraction", "name": "Điểm chưa phân loại ZZZ",
                          "summary": "x"})  # placeId rỗng

        # xuất hiện trong danh sách chưa phân loại
        lst = client_mocked.get("/admin/unclassified?q=ZZZ", headers=hdr)
        assert lst.status_code == 200, lst.text
        assert any(e["id"] == "ent-unclass-1" for e in lst.json()["entities"])

        # gán vào place không hợp lệ -> 400
        bad = client_mocked.post("/admin/entities/ent-unclass-1/place", headers=hdr,
                                 json={"place_id": "ent-unclass-1"})  # không phải place
        assert bad.status_code == 400

        # gán đúng xã -> reflected ở DB + area đồng bộ
        ok = client_mocked.post("/admin/entities/ent-unclass-1/place", headers=hdr,
                                json={"place_id": "xa-assign-test"})
        assert ok.status_code == 200, ok.text
        got = db.get_entity("ent-unclass-1")
        assert got["placeId"] == "xa-assign-test" and got["area"] == "vinh-long"
    finally:
        for i in seeded:
            db.delete_entity(i)


def test_admin_ai_triage_endpoint(client_mocked):
    """On-demand agent: POST /admin/ai/triage trả 200 + context kể cả khi LLM hỏng (degrade);
    yêu cầu admin."""
    from middleware import ADMIN_API_KEY as _ADMIN_KEY
    # ẩn danh bị chặn
    assert client_mocked.post("/admin/ai/triage").status_code == 401
    r = client_mocked.post("/admin/ai/triage", headers={"X-Admin-Key": _ADMIN_KEY})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "context" in body          # luôn có tình hình thô
    assert "ok" in body               # ok=True nếu LLM chạy, False nếu hỏng — đều 200


def test_internal_endpoints_gated_in_prod(client_mocked, monkeypatch):
    """GĐ4 phụ (a): ở production, /system/*, /analytics/*, /metrics ẩn sau admin key (404 nếu thiếu);
    dev thì mở. Nuxt không gọi trực tiếp các path này."""
    from middleware import ADMIN_API_KEY as _ADMIN_KEY

    # Dev (mặc định): /metrics mở
    monkeypatch.setattr(server, "_IS_PROD", False)
    assert client_mocked.get("/metrics").status_code == 200

    # Prod: ẩn nếu không có key
    monkeypatch.setattr(server, "_IS_PROD", True)
    assert client_mocked.get("/metrics").status_code == 404
    assert client_mocked.get("/system/logs").status_code == 404
    assert client_mocked.get("/analytics/summary").status_code == 404
    # Có admin key -> qua middleware (200 hoặc lỗi nội bộ endpoint, miễn KHÔNG phải 404-gate)
    assert client_mocked.get("/metrics", headers={"X-Admin-Key": _ADMIN_KEY}).status_code == 200
    # Path công khai vẫn mở ở prod
    assert client_mocked.get("/health").status_code == 200


def test_info_report_submit_and_admin_list(client_mocked, tmp_path, monkeypatch):
    """GĐ13.6f: POST /api/report (ẩn danh, JSONL) ghi nhận; admin xem qua /admin/info-reports;
    rate-limit chặn spam. Tách khỏi UGC `reports` (Postgres)."""
    import public_api
    import admin as admin_mod
    from middleware import report_limiter, ADMIN_API_KEY as _ADMIN_KEY

    rfile = tmp_path / "reports.jsonl"
    monkeypatch.setattr(public_api, "REPORTS_FILE", rfile)
    monkeypatch.setattr(admin_mod, "_INFO_REPORTS_FILE", rfile)
    report_limiter._requests.clear()  # state sạch (singleton toàn cục)

    # 1) Gửi báo-sai hợp lệ
    r = client_mocked.post("/api/report", json={
        "target_id": "ubnd-xa-test", "target_type": "facility",
        "reason": "Sai số điện thoại", "detail": "SĐT đúng là 0270 111 222"})
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    assert rfile.exists()

    # target_type lạ -> chuẩn hoá "other"
    r2 = client_mocked.post("/api/report", json={
        "target_id": "x", "target_type": "weird", "reason": "test"})
    assert r2.status_code == 200, r2.text

    # 2) Admin liệt kê (mới nhất trước)
    hdr = {"X-Admin-Key": _ADMIN_KEY}
    lst = client_mocked.get("/admin/info-reports", headers=hdr)
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body["total"] == 2
    assert body["reports"][0]["target_id"] == "x"
    assert body["reports"][0]["target_type"] == "other"
    assert body["reports"][1]["reason"] == "Sai số điện thoại"

    # admin endpoint yêu cầu auth
    assert client_mocked.get("/admin/info-reports").status_code == 401

    # 3) Rate-limit: limiter cho 5/5min — đã dùng 2, gửi thêm tới khi 429
    last = None
    for _ in range(6):
        last = client_mocked.post("/api/report", json={"target_id": "y", "reason": "spam"})
    assert last.status_code == 429, last.text
    assert last.json().get("error") == "rate_limited"


def test_entities_month_pagination(client_mocked):
    """GĐ-audit: /api/entities?month= phải lọc TOÀN BỘ tập rồi mới phân trang → total đúng
    + limit/offset đúng (trước đây lọc sau khi đã phân trang → total sai, trang thiếu)."""
    from database import db
    seeded = [f"m-seed-{i}" for i in range(5)]
    try:
        for i in range(5):  # 5 entity đều vào mùa tháng 7
            db.upsert_entity({"id": f"m-seed-{i}", "type": "experience", "name": f"Mùa 7 #{i}",
                              "summary": "x", "season": {"months": [7]}})
        r = client_mocked.get("/api/entities?month=7&limit=2&offset=0")
        assert r.status_code == 200, r.text
        body = r.json()
        # total phản ánh TOÀN BỘ entity tháng 7 (>=5), không phải chỉ trang hiện tại
        assert body["total"] >= 5, body["total"]
        assert len(body["entities"]) == 2  # limit tôn trọng
        # trang 2 có dữ liệu (trước fix có thể rỗng)
        r2 = client_mocked.get("/api/entities?month=7&limit=2&offset=2")
        assert len(r2.json()["entities"]) >= 1
    finally:
        for eid in seeded:
            db.delete_entity(eid)


def test_place_overview_endpoint(client_mocked):
    """Trang hub xã/phường: /api/places/{id}/overview gom danh bạ + du lịch + lưu trú + sản phẩm.
    404 nếu id không phải place."""
    from database import db  # admin editor không cho type=place → seed thẳng DB

    seeded = ["xa-test-hub", "diem-hub-1", "ks-hub-1", "sp-hub-1"]
    try:
        db.upsert_entity({"id": "xa-test-hub", "type": "place", "name": "Xã Test Hub",
                          "area": "vinh-long", "level": "xa"})
        db.upsert_entity({"id": "diem-hub-1", "type": "attraction", "name": "Điểm Hub 1",
                          "summary": "x", "placeId": "xa-test-hub"})
        db.upsert_entity({"id": "ks-hub-1", "type": "accommodation", "name": "KS Hub 1",
                          "summary": "x", "placeId": "xa-test-hub"})
        db.upsert_entity({"id": "sp-hub-1", "type": "product", "name": "SP Hub 1",
                          "summary": "x", "placeId": "xa-test-hub"})

        ov = client_mocked.get("/api/places/xa-test-hub/overview")
        assert ov.status_code == 200, ov.text
        body = ov.json()
        assert body["place"]["name"] == "Xã Test Hub"
        assert body["counts"]["tourism"] == 1
        assert body["counts"]["lodging"] == 1
        assert body["counts"]["products"] == 1
        assert isinstance(body["facilities"], list)  # rỗng đến khi có dữ liệu thật
        assert {e["id"] for e in body["tourism"]} == {"diem-hub-1"}

        # id không phải place -> 404
        assert client_mocked.get("/api/places/diem-hub-1/overview").status_code == 404
    finally:
        for eid in seeded:
            db.delete_entity(eid)


def test_directory_lookup_tool_dispatch(client_mocked):
    """GĐ13: chat-tool `directory_lookup` -> knowledge.directory_search; trả note rõ khi rỗng,
    trả results khi có facility. Bao phủ nhánh dispatch trong call_tool."""
    import json as _json

    import knowledge

    # Chưa có dữ liệu -> note rõ ràng, không bịa
    empty = _json.loads(server.call_tool("directory_lookup", {"query": "UBND xã không tồn tại 999"}))
    assert empty["results"] == []
    assert "danh bạ" in empty["note"].lower()

    # Bơm tạm 1 facility vào KB in-memory rồi tra
    fac = {
        "id": "ubnd-test-gd13", "name": "UBND xã Test GĐ13", "type": "facility",
        "placeId": None,
        "attributes": {"office_kind": "ubnd", "address": "123 Đường Test", "phone": "0270 999 888"},
        "source": {"url": "https://vinhlong.gov.vn"},
    }
    knowledge._entities[fac["id"]] = fac
    try:
        got = _json.loads(server.call_tool("directory_lookup", {"query": "UBND xã Test"}))
        assert any(r["name"] == "UBND xã Test GĐ13" and r["phone"] == "0270 999 888"
                   for r in got["results"])
    finally:
        knowledge._entities.pop(fac["id"], None)

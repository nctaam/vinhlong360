# TẠM THỜI — detective tìm test làm rỗng router (pollution). XOÁ sau khi xong.
import sys

_prev = {}
_flagged = set()


def pytest_runtest_teardown(item, nextitem):
    try:
        if "agent" not in sys.path:
            sys.path.insert(0, "agent")
        for mod in ("admin", "social", "auth", "notifications", "public_api"):
            m = sys.modules.get(mod)
            if m is None:
                if mod not in _flagged:
                    sys.stderr.write(f"\n[ROUTER-NOMOD] {item.nodeid} -> {mod} not in sys.modules\n")
                    _flagged.add(mod)
                continue
            if not hasattr(m, "router"):
                continue
            n = len(m.router.routes)
            p = _prev.get(mod)
            if p is not None and n < p - 5:
                sys.stderr.write(f"\n[POLLUTER] {item.nodeid} -> {mod}.router {p}->{n}\n")
                sys.stderr.flush()
            # Cờ khi count thấp bất thường (bắt cả always-empty-from-start)
            key = (mod, n < 30)
            if n < 30 and key not in _flagged:
                sys.stderr.write(f"\n[ROUTER-LOW] {item.nodeid} -> {mod}.router={n}\n")
                sys.stderr.flush()
                _flagged.add(key)
            _prev[mod] = n
    except Exception as e:
        sys.stderr.write(f"\n[DETECTIVE-ERR] {e}\n")

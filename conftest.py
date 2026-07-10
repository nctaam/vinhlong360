# TẠM THỜI — detective tìm test làm rỗng router (pollution). XOÁ sau khi xong.
import sys

_prev = {}


def pytest_runtest_teardown(item, nextitem):
    try:
        if "agent" not in sys.path:
            sys.path.insert(0, "agent")
        for mod in ("admin", "social", "auth", "notifications", "public_api"):
            m = sys.modules.get(mod)
            if m is not None and hasattr(m, "router"):
                n = len(m.router.routes)
                p = _prev.get(mod)
                if p is not None and n < p - 5:
                    sys.stderr.write(f"\n[POLLUTER] {item.nodeid} -> {mod}.router {p}->{n}\n")
                    sys.stderr.flush()
                _prev[mod] = n
    except Exception:
        pass

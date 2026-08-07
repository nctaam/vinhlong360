"""Cổng lắng nghe của các tiến trình Python — đọc từ env, mặc định = cổng hiện hành.

Vì sao có file này: vinhlong360 là NỀN TẢNG sẽ được nhân bản (dongthap360,
cantho360…), mỗi bản một VPS + một DB riêng — xem
`docs/superpowers/specs/2026-07-13-dongthap360-fork-design.md`. Port ghim cứng
trong ``uvicorn.run(...)`` là thứ chặn đầu tiên khi cần chạy hai bản trên cùng
một máy (dù chỉ để đối chiếu), vì hai tiến trình không chia nhau được một cổng.

Bất biến: KHÔNG set env => hành vi y hệt trước (agent 8360, bot gateway 8361).

Mỗi tiến trình đọc MỘT biến riêng (``AGENT_PORT`` vs ``BOT_GATEWAY_PORT``) —
dùng chung một biến thì đổi cổng agent sẽ kéo theo bot gateway nhảy cổng, đúng
kiểu lỗi chỉ lộ ra lúc chạy thật.

⚠ Đổi cổng ở env KHÔNG tự sửa `nginx.conf`, `nginx-ssl.conf`, `ops/systemd/*`,
`docker-compose*.yml` (đang ghim 8360/8361). Đổi một bên = nginx proxy vào cổng
trống. Sửa kèm hạ tầng là việc của chủ dự án (CLAUDE.md §4 — deploy config).
"""

from __future__ import annotations

import os

MIN_PORT = 1
MAX_PORT = 65535


class PortConfigError(ValueError):
    """Giá trị cổng trong env không dùng được — nêu rõ biến nào sai, sai chỗ nào.

    Kế thừa ``ValueError`` để code cũ bắt ``ValueError`` vẫn bắt được.
    """


def resolve_port(env_name: str, default: int) -> int:
    """Trả về cổng lắng nghe cho tiến trình; ``default`` khi env không đặt.

    Rỗng/toàn khoảng trắng cũng tính là "không đặt" — docker-compose và systemd
    thường truyền biến rỗng, không nên coi đó là lỗi cấu hình.

    Giá trị RÁC thì **fail nhanh, không âm thầm rơi về default**: nếu hai bản
    clone cùng gõ sai rồi cùng rơi về 8360, bản thứ hai chết vì "address already
    in use" ở tầng khác, hoặc tệ hơn là chiếm cổng của bản kia. Báo đúng tên
    biến + giá trị sai ngay tại chỗ rẻ hơn nhiều.
    """
    raw = os.environ.get(env_name)
    if raw is None or not raw.strip():
        return default

    value = raw.strip()
    try:
        port = int(value)
    except ValueError:
        raise PortConfigError(
            f"{env_name}={raw!r} không phải số nguyên. Đặt số cổng "
            f"({MIN_PORT}-{MAX_PORT}), hoặc bỏ trống để dùng mặc định {default}."
        ) from None

    if not (MIN_PORT <= port <= MAX_PORT):
        raise PortConfigError(
            f"{env_name}={raw!r} ngoài khoảng cổng hợp lệ {MIN_PORT}-{MAX_PORT}. "
            f"Bỏ trống để dùng mặc định {default}."
        )

    return port

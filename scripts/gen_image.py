#!/usr/bin/env python3
"""Sinh ảnh qua endpoint ChatGPT-compatible (cx/gpt-5.5-image) → lưu file.

Dùng cho ảnh UI (hero/OG/placeholder/illustration) — nguồn AI-generated, sạch
bản quyền (hợp §B6, khác cào ảnh gov/báo). Endpoint local do chủ dự án cấp.

SECRET: KHÔNG hardcode API key. Đọc từ env IMAGE_API_KEY (bắt buộc).
  PowerShell:  $env:IMAGE_API_KEY='sk-...'; python scripts/gen_image.py --prompt "..." --out web-nuxt/public/img/hero.jpg
  Bash:        IMAGE_API_KEY=sk-... python scripts/gen_image.py --prompt "..." --out ...

Response là SSE; ảnh nằm trong field b64_json (lấy bản dài nhất = ảnh hoàn chỉnh).
"""
import argparse, base64, json, os, re, sys, urllib.request

API_BASE = os.environ.get("IMAGE_API_BASE", "http://localhost:20128")
API_KEY = os.environ.get("IMAGE_API_KEY", "")
MODEL = os.environ.get("IMAGE_MODEL", "cx/gpt-5.5-image")


def generate(prompt: str, out: str, size: str = "auto", quality: str = "auto",
             fmt: str = "jpeg", detail: str = "high", timeout: int = 180) -> str:
    if not API_KEY:
        sys.exit("ERROR: đặt env IMAGE_API_KEY trước khi chạy (không hardcode trong repo).")
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "n": 1, "size": size,
        "quality": quality, "background": "auto", "image_detail": detail,
        "output_format": fmt,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/v1/images/generations", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}",
                 "Accept": "text/event-stream"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8", "replace")
    b64s = re.findall(r'"b64_json":"([A-Za-z0-9+/=]+)"', data)
    if not b64s:
        err = re.search(r'"(?:error|message)":"([^"]+)"', data)
        sys.exit(f"ERROR: không thấy ảnh trong response. {err.group(1) if err else data[:300]}")
    img = base64.b64decode(max(b64s, key=len))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(img)
    print(f"OK: {out}  ({len(img)} bytes, magic {img[:3].hex()})")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="auto", help='vd "1536x1024", "1024x1024", "auto"')
    ap.add_argument("--quality", default="auto")
    ap.add_argument("--format", default="jpeg")
    ap.add_argument("--detail", default="high")
    a = ap.parse_args()
    generate(a.prompt, a.out, a.size, a.quality, a.format, a.detail)

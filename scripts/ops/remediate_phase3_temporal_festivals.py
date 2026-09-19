# -*- coding: utf-8 -*-
"""Remediate Phase 3: Synchronize 24 festival date conflicts between Gregorian, Lunar calendar, and seasonality."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")

def remediate_phase3():
    print(f"Reading {DATA_PATH}...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    entity_map = {e["id"]: e for e in entities}
    changes = []

    festivals_sync = {
        "le-hoi-lang-ong-tien-quan-thong-che-dieu-bat-nguyen-van-ton": {
            "date_start": "2026-02-20",
            "date_end": "2026-02-21",
            "lunar_date": "Mùng 3–4 tháng Giêng âm lịch",
            "season": {
                "peak": [2],
                "months": [2],
                "text": "Lễ hội Lăng Ông Tiền quân Thống chế Điều bát Nguyễn Văn Tồn diễn ra vào mùng 3-4 tháng Giêng âm lịch (khoảng tháng 2 dương lịch)."
            }
        },
        "lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-": {
            "date_start": "2026-02-20",
            "date_end": "2026-02-21",
            "lunar_date": "Mùng 3–4 tháng Giêng âm lịch",
            "season": {
                "peak": [2],
                "months": [2],
                "text": "Lễ hội Lăng Ông Tiền quân Thống chế Điều bát Nguyễn Văn Tồn diễn ra vào mùng 3-4 tháng Giêng âm lịch (khoảng tháng 2 dương lịch)."
            }
        },
        "le-thuong-dien-dinh-tan-ngai": {
            "date_start": "2026-11-24",
            "date_end": "2026-11-25",
            "lunar_date": "16–17 tháng 10 âm lịch",
            "season": {
                "peak": [11],
                "months": [11],
                "text": "Lễ Thượng điền Đình Tân Ngãi diễn ra vào ngày 16-17 tháng 10 âm lịch (tháng 11 dương lịch)."
            }
        },
        "le-hoi-dom-long-neak-ta": {
            "date_start": None,
            "date_end": None,
            "lunar_date": "Tháng 3–5 âm lịch (tùy từng phum sóc)",
            "season": {
                "peak": [4, 5],
                "months": [4, 5],
                "text": "Lễ hội Đom Lơng Néak Tà diễn ra vào thời điểm giao mùa từ nắng sang mưa, khoảng tháng 4-5 dương lịch (tháng 3-5 âm lịch tùy từng phum sóc)."
            }
        },
        "le-gio-nguyen-dinh-chieu": {
            "date_start": "2026-07-01",
            "date_end": "2026-07-03",
            "lunar_date": "Tổ chức theo ngày dương lịch: 01-03/7 (Kỷ niệm ngày mất 03/7/1888 DL của Cụ Đồ Chiểu)",
            "season": {
                "peak": [7],
                "months": [7],
                "text": "Ngày hội Truyền thống Văn hóa Ba Tri tổ chức từ ngày 1 đến 3 tháng 7 dương lịch hằng năm tại khu lưu niệm."
            }
        },
        "le-gio-phan-thanh-gian-tai-van-thanh-mieu": {
            "date_start": "2026-08-16",
            "date_end": "2026-08-17",
            "lunar_date": "Mùng 4–5 tháng 7 âm lịch",
            "season": {
                "peak": [8],
                "months": [8],
                "text": "Lễ giỗ Phan Thanh Giản tại Văn Thánh Miếu Vĩnh Long diễn ra vào mùng 4-5 tháng 7 âm lịch (khoảng tháng 8 dương lịch)."
            }
        },
        "le-hoi-van-thanh-mieu": {
            "date_start": "2026-03-28",
            "date_end": "2026-03-29",
            "lunar_date": "Ngày Đinh tháng 2 âm lịch (Lễ Xuân Đinh)",
            "season": {
                "peak": [3],
                "months": [3],
                "text": "Lễ Xuân Đinh diễn ra vào tháng 2 âm lịch (tháng 3 dương lịch) tại Văn Thánh Miếu."
            }
        },
        "le-via-ba-co-hy": {
            "date_start": "2026-03-03",
            "date_end": "2026-03-03",
            "lunar_date": "Rằm (15) tháng Giêng âm lịch",
            "season": {
                "peak": [3],
                "months": [3],
                "text": "Lễ Vía Bà Cố Hỷ diễn ra vào Rằm tháng Giêng âm lịch (khoảng đầu tháng 3 dương lịch năm 2026)."
            }
        },
        "le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu": {
            "date_start": "2026-04-02",
            "date_end": "2026-04-03",
            "lunar_date": "15–16 tháng 2 âm lịch",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Lễ hội của ngư dân vùng biển Thạnh Hải diễn ra vào ngày 15–16 tháng 2 âm lịch (đầu tháng 4 dương lịch năm 2026)."
            }
        },
        "le-hoi-nghinh-ong-lang-con-tau": {
            "date_start": "2026-04-26",
            "date_end": "2026-04-27",
            "lunar_date": "10–11 tháng 3 âm lịch",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Lễ hội Nghinh Ông Lăng Cồn Tàu tổ chức vào ngày 10–11 tháng 3 âm lịch (cuối tháng 4 dương lịch năm 2026)."
            }
        },
        "le-hoi-nghinh-ong-duyen-hai": {
            "date_start": "2026-04-26",
            "date_end": "2026-04-28",
            "lunar_date": "10–12 tháng 3 âm lịch",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Lễ hội Nghinh Ông Duyên Hải tổ chức từ ngày 10 đến 12 tháng 3 âm lịch (khoảng cuối tháng 4 dương lịch năm 2026)."
            }
        },
        "le-ha-dien-dinh-tan-hoa": {
            "date_start": "2026-04-30",
            "date_end": "2026-05-01",
            "lunar_date": "14–15 tháng 3 âm lịch",
            "season": {
                "peak": [4, 5],
                "months": [4, 5],
                "text": "Lễ Hạ điền Đình Tân Hoa tổ chức vào ngày 14-15 tháng 3 âm lịch (cuối tháng 4, đầu tháng 5 dương lịch năm 2026)."
            }
        },
        "le-hoi-ky-yen": {
            "date_start": "2026-04-03",
            "date_end": "2026-04-04",
            "lunar_date": "16–17 tháng 2 âm lịch (hoặc theo lệ mùa xuân từng đình làng)",
            "season": {
                "peak": [3, 4],
                "months": [3, 4],
                "text": "Lễ hội Kỳ Yên đình làng Nam Bộ diễn ra cao điểm vào các tháng 2-3 âm lịch (tháng 3-4 dương lịch)."
            }
        },
        "le-hoi-chol-chnam-thmay-va-sen-dolta": {
            "date_start": "2026-04-13",
            "date_end": "2026-04-16",
            "lunar_date": "Chôl Chnăm Thmây: 13–16/4 DL; Sên Đôn Ta: 29/8–01/9 ÂL",
            "season": {
                "peak": [4, 10],
                "months": [4, 9, 10],
                "text": "Chôl Chnăm Thmây diễn ra vào giữa tháng 4 dương lịch, Sên Đôn Ta diễn ra vào cuối tháng 8 đầu tháng 9 âm lịch (tháng 9-10 dương lịch)."
            }
        },
        "le-hoi-chol-chnam-thmay-tai-chua-ky-son": {
            "date_start": "2026-04-13",
            "date_end": "2026-04-16",
            "lunar_date": "Cố định theo dương lịch: 13–16 tháng 4",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Lễ hội Chôl Chnăm Thmây tại chùa Kỳ Son tổ chức từ ngày 13 đến 16 tháng 4 dương lịch hàng năm."
            }
        },
        "le-chol-chhnam-thmay": {
            "date_start": "2026-04-13",
            "date_end": "2026-04-16",
            "lunar_date": "Cố định theo dương lịch: 13–16 tháng 4",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Chôl Chnăm Thmây là Tết năm mới của người Khmer Nam Bộ, diễn ra từ ngày 13 đến 16 tháng 4 dương lịch hàng năm."
            }
        },
        "le-hoi-nguyen-tieu": {
            "date_start": "2026-03-03",
            "date_end": "2026-03-03",
            "lunar_date": "Rằm (15) tháng Giêng âm lịch",
            "season": {
                "peak": [3],
                "months": [3],
                "text": "Lễ hội Nguyên Tiêu diễn ra vào đêm Rằm tháng Giêng âm lịch (đầu tháng 3 dương lịch năm 2026)."
            }
        },
        "le-hoi-nguyen-tieu-o-tra-cu": {
            "date_start": "2026-03-03",
            "date_end": "2026-03-03",
            "lunar_date": "Rằm (15) tháng Giêng âm lịch",
            "season": {
                "peak": [3],
                "months": [3],
                "text": "Lễ hội Nguyên Tiêu truyền thống Triều Châu ở Trà Cú tổ chức vào Rằm tháng Giêng âm lịch."
            }
        },
        "tet-doan-ngo": {
            "date_start": "2026-06-19",
            "date_end": "2026-06-19",
            "lunar_date": "Mùng 5 tháng 5 âm lịch",
            "season": {
                "peak": [6],
                "months": [6],
                "text": "Tết Đoan Ngọ diễn ra vào ngày mùng 5 tháng 5 âm lịch (khoảng trung tuần tháng 6 dương lịch)."
            }
        },
        "tet-nguyen-dan-mien-tay": {
            "date_start": "2026-02-17",
            "date_end": "2026-02-19",
            "lunar_date": "Mùng 1 đến mùng 3 tháng Giêng âm lịch",
            "season": {
                "peak": [2],
                "months": [1, 2],
                "text": "Tết Nguyên Đán cổ truyền diễn ra từ mùng 1 đến mùng 3 tháng Giêng âm lịch (tháng 2 dương lịch)."
            }
        },
        "le-vu-lan": {
            "date_start": "2026-08-27",
            "date_end": "2026-08-27",
            "lunar_date": "Rằm (15) tháng 7 âm lịch",
            "season": {
                "peak": [8],
                "months": [8],
                "text": "Đại lễ Vu Lan báo hiếu tổ chức vào ngày Rằm tháng 7 âm lịch (cuối tháng 8 dương lịch năm 2026)."
            }
        },
        "le-gio-to-hung-vuong": {
            "date_start": "2026-04-26",
            "date_end": "2026-04-26",
            "lunar_date": "Mùng 10 tháng 3 âm lịch",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Ngày Giỗ Tổ Hùng Vương diễn ra vào mùng 10 tháng 3 âm lịch (khoảng cuối tháng 4 dương lịch năm 2026)."
            }
        },
        "le-hoi-cau-ngu": {
            "date_start": "2026-04-02",
            "date_end": "2026-04-02",
            "lunar_date": "Rằm (15) tháng 2 âm lịch",
            "season": {
                "peak": [4],
                "months": [4],
                "text": "Lễ hội Cầu ngư cúng biển Ba Động tổ chức vào ngày Rằm tháng 2 âm lịch (đầu tháng 4 dương lịch năm 2026)."
            }
        },
        "le-hoi-long-den": {
            "date_start": "2026-09-25",
            "date_end": "2026-09-25",
            "lunar_date": "Rằm (15) tháng 8 âm lịch (Tết Trung Thu)",
            "season": {
                "peak": [9],
                "months": [9],
                "text": "Lễ hội rước đèn lồng Trung Thu tổ chức vào đêm Rằm tháng 8 âm lịch (cuối tháng 9 dương lịch năm 2026)."
            }
        },
        "le-hoi-ba-chua-xu": {
            "date_start": "2026-05-09",
            "date_end": "2026-05-13",
            "lunar_date": "23–27 tháng 3 âm lịch",
            "season": {
                "peak": [5],
                "months": [5],
                "text": "Lễ hội Vía Bà Chúa Xứ diễn ra từ ngày 23 đến 27 tháng 3 âm lịch (tháng 5 dương lịch năm 2026)."
            }
        }
    }

    for fid, sync_vals in festivals_sync.items():
        if fid in entity_map:
            ent = entity_map[fid]
            attrs = ent.setdefault("attributes", {})
            old_snapshot = {
                "date_start": ent.get("date_start") or attrs.get("date_start"),
                "date_end": ent.get("date_end") or attrs.get("date_end"),
                "lunar_date": attrs.get("lunar_date"),
                "season": ent.get("season")
            }

            # Update fields on both root and attributes if present
            if "date_start" in ent:
                ent["date_start"] = sync_vals["date_start"]
            attrs["date_start"] = sync_vals["date_start"]

            if "date_end" in ent:
                ent["date_end"] = sync_vals["date_end"]
            attrs["date_end"] = sync_vals["date_end"]

            attrs["lunar_date"] = sync_vals["lunar_date"]
            ent["season"] = sync_vals["season"]

            changes.append({
                "entity_id": fid,
                "field": "date_start, date_end, lunar_date, season",
                "old": old_snapshot,
                "new": sync_vals,
                "reason": "Harmonize astronomical lunar-solar date and season cross-field alignment"
            })

    print(f"Applied {len(changes)} changes in Phase 3.")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Successfully saved {DATA_PATH}.")

    log_path = Path("outputs/remediation_phase3_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)
    print(f"Saved audit log to {log_path}.")

if __name__ == "__main__":
    remediate_phase3()

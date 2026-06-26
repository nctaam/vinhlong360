"""Áp dụng rewrite summary (đơn vị HC cũ → 2 cấp) — CHỈ khi qua verify chống-bịa.
Nguồn: scratch/rw_out/out_*.json (rewrite) + scratch/rw_verify/v_*.json (LLM verdict).
VERIFY DETERMINISTIC (lớp §1.4 chính):
  - new KHÔNG còn 'huyện <Hoa>' (trừ Lộ/Lô) và KHÔNG còn 'tỉnh Bến Tre/Trà Vinh'.
  - KHÔNG bịa: token-có-nghĩa (Hoa-đầu / chứa-số) trong new \\ old ⊆ {vĩnh, long}.
  - KHÔNG mất năm: mọi số 4-chữ-số trong old phải còn trong new.
  - KHÔNG cắt quá tay: len(new) ≥ 0.6·len(old).
ACCEPT = det_pass AND (LLM verdict != false). DRY-RUN mặc định; --apply để ghi. §B1 backup.
"""
import json, re, sys, unicodedata, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv

OBJ = re.compile(r'"id"\s*:\s*"([^"]+)"\s*,\s*"new_summary"\s*:\s*"(.*?)"\s*,\s*"changed"\s*:\s*(true|false)', re.S)
def load_out(f):
    txt = open(f, encoding="utf-8").read()
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # agent quên escape " bên trong → cứu bằng regex (verify-det vẫn chặn cuối)
        out=[]
        for m in OBJ.finditer(txt):
            out.append({"id":m.group(1), "new_summary":m.group(2), "changed":m.group(3)=="true"})
        print(f"  [recover] {f}: regex cứu {len(out)} item")
        return out

# gom rewrite + verdict
rw = {}
for f in sorted(glob.glob(str(ROOT/"scratch/rw_out/out_*.json"))):
    for it in load_out(f):
        rw[it["id"]] = it
vf = {}
for f in sorted(glob.glob(str(ROOT/"scratch/rw_verify/v_*.json"))):
    try:
        with open(f, encoding="utf-8") as fh:
            items = json.load(fh)
        for it in items:
            vf[it["id"]] = it
    except Exception:
        pass

with open(DATA, encoding="utf-8") as f:
    d = json.load(f)
byid = {e["id"]: e for e in d["entities"]}

HUYEN_NEW = re.compile(r"\bhuyện\s+(?!lộ\b|lô\b|lo\b)[A-ZĐ]")
PROV_OLD  = re.compile(r"\btỉnh\s+(?:Bến Tre|Trà Vinh)\b")
YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")
def sigtokens(s):  # token có-nghĩa: bắt đầu Hoa (kể cả dấu) HOẶC chứa số
    out=set()
    for w in re.findall(r"[^\s,.;:()\[\]\"'/]+", unicodedata.normalize("NFC", s)):
        if any(ch.isdigit() for ch in w) or (w[:1].isupper()):
            out.add(w.lower().strip("-–"))
    return out

applied=[]; rejected=[]; samples=[]
for eid, it in rw.items():
    if not it.get("changed"): continue
    e = byid.get(eid)
    if not e: rejected.append((eid,"no-entity")); continue
    old = e.get("summary") or ""
    new = it.get("new_summary") or ""
    if not new or new == old: continue
    reasons=[]
    if HUYEN_NEW.search(new): reasons.append("còn 'huyện X'")
    if PROV_OLD.search(new): reasons.append("còn tỉnh cũ")
    adds = sigtokens(new) - sigtokens(old) - {"vĩnh","long","tỉnh"}
    if adds: reasons.append("BỊA: "+",".join(sorted(adds))[:60])
    lost_year = set(YEAR.findall(old)) - set(YEAR.findall(new))
    if lost_year: reasons.append("mất năm "+",".join(lost_year))
    # brand-guard: 'Bến Tre'/'Trà Vinh' KHÔNG kèm 'tỉnh' = thương hiệu/bản sắc → phải giữ
    nonprov = lambda s: len(re.findall(r"\b(?:Bến Tre|Trà Vinh)\b", s)) - len(re.findall(r"tỉnh\s+(?:Bến Tre|Trà Vinh)\b", s))
    if nonprov(new) < nonprov(old): reasons.append("đổi brand 'Bến Tre/Trà Vinh' (không kèm tỉnh)")
    if len(new) < 0.6*len(old): reasons.append(f"cắt quá ({len(new)}/{len(old)})")
    v = vf.get(eid)
    if v and v.get("ok") is False: reasons.append("LLM-veto: "+str(v.get("reason"))[:50])
    if reasons:
        rejected.append((eid, " | ".join(reasons))); continue
    if APPLY: e["summary"] = new
    applied.append(eid)
    if len(samples) < 12: samples.append((eid, old, new))

print(f"=== APPLY SUMMARY REWRITE — {'APPLY' if APPLY else 'DRY-RUN'} ===")
print(f"  rewrite changed: {sum(1 for it in rw.values() if it.get('changed'))} | LLM verdicts: {len(vf)}")
print(f"  ACCEPT: {len(applied)} | REJECT: {len(rejected)}")
print("\n  --- REJECT (mẫu 20) ---")
for r in rejected[:20]: print("   ✗", r[0], "→", r[1])
print("\n  --- DIFF mẫu (accepted) ---")
for eid, old, new in samples[:8]:
    print(f"\n   [{eid}]")
    print(f"     OLD: {old[:200]}")
    print(f"     NEW: {new[:200]}")
if APPLY:
    json.dump(d, open(DATA,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  ✅ ĐÃ GHI {DATA} ({len(applied)} summary)")
else:
    print("\n  (DRY-RUN — chưa ghi)")

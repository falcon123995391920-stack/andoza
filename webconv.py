"""Sayt formasi <-> ichki ma'lumot (person) almashtirish."""
from __future__ import annotations

import re

import core

_ws = core._ws
OY = ["январдан", "февралдан", "мартдан", "апрелдан", "майдан", "июндан",
      "июлдан", "августдан", "сентябрдан", "октябрдан", "ноябрдан", "декабрдан"]
LANGS = ["рус", "инглиз", "немис", "француз", "испан", "итальян", "турк", "араб", "хитой", "япон", "корейс"]


# ---------------------------------------------------------------- sanalar
def date_norm(s: str) -> str:
    return core._fix_date(s)


def job_since_compose(d: str) -> str:
    """'01.05.2024' -> '2024 йил 1 майдан:'"""
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_norm(d))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return ""
    return f"{m.group(3)} йил {int(m.group(1))} {OY[int(m.group(2)) - 1]}:"


def job_since_split(s: str) -> str:
    m = re.match(r"\s*(\d{4})\s*йил\s*(\d{1,2})\s+([а-яўқғҳ]+?)дан", s or "", re.I)
    if m:
        for i, name in enumerate(OY, 1):
            if name.startswith(m.group(3).lower()):
                return f"{int(m.group(2)):02d}.{i:02d}.{m.group(1)}"
    return ""


# ---------------------------------------------------------------- davr
def period_compose(row: dict) -> str:
    a = str(row.get("from", "") or "").strip()
    b = str(row.get("to", "") or "").strip()
    if not a:
        return str(row.get("raw", "") or "").strip()
    if row.get("present"):
        return f"{a} й.  -  ҳ.в."
    return core._fix_period(f"{a}-{b}" if b else a)


def period_decompose(period: str) -> dict:
    p = core._fix_period(period)
    m = re.fullmatch(r"(\d{4})-(\d{4}) йй\.", p)
    if m:
        return {"from": m.group(1), "to": m.group(2), "present": False, "raw": ""}
    m = re.fullmatch(r"(\d{4}) й\.  -  ҳ\.в\.", p)
    if m:
        return {"from": m.group(1), "to": "", "present": True, "raw": ""}
    m = re.fullmatch(r"(\d{4}) й\.", p)
    if m:
        return {"from": m.group(1), "to": "", "present": False, "raw": ""}
    return {"from": "", "to": "", "present": False, "raw": p}


# ---------------------------------------------------------------- qarindosh
def rel_from_web(r: dict) -> dict:
    year, place = _ws(r.get("year")), _ws(r.get("place"))
    rel = core.make_relative(r.get("relation", ""), r.get("fio", ""), year or "0", place,
                             r.get("status") or "works", work=r.get("work", ""),
                             residence=r.get("residence", ""), death_year=r.get("death_year", ""))
    if not year:
        rel["birth"] = place
    return rel


def rel_to_web(rel: dict) -> dict:
    birth, work = _ws(rel.get("birth")), _ws(rel.get("work"))
    m = re.match(r"^(\d{4})\s*йил\s*,?\s*(.*)$", birth)
    year, place = (m.group(1), m.group(2)) if m else ("", birth)
    status, death, wk = "works", "", work
    md = re.match(r"^(?:(\d{4})\s+йил\s+)?вафот\s+этган(?:\s*\((.*)\))?$", work, re.I)
    mp = re.match(r"^Пенсияда(?:\s*\((.*)\))?$", work, re.I)
    if md:
        status, death, wk = "dead", md.group(1) or "", md.group(2) or ""
    elif mp:
        status, wk = "pension", mp.group(1) or ""
    return {"relation": rel.get("relation", ""), "fio": rel.get("fio", ""), "year": year, "place": place,
            "status": status, "death_year": death, "work": wk,
            "residence": "" if status == "dead" else rel.get("residence", ""),
            "auto": bool(rel.get("auto"))}


# ---------------------------------------------------------------- tillar
def langs_compose(chips: list, other: str) -> str:
    names = [c for c in chips or [] if c] + [_ws(x) for x in re.split(r"[,;]", other or "") if _ws(x)]
    if not names:
        return ""
    return f"{names[0]} тили" if len(names) == 1 else ", ".join(names) + " тиллари"


def langs_split(s: str):
    t = re.sub(r"\s*тил(?:и|лари)\s*\.?$", "", _ws(s), flags=re.I)
    if not t or t.lower().rstrip(".") == core.NONE_WORD:
        return [], ""
    parts = [x.strip() for x in re.split(r"[,;]", t) if x.strip()]
    chips = [x for x in parts if x in LANGS]
    other = ", ".join(x for x in parts if x not in LANGS)
    return chips, other


# ---------------------------------------------------------------- yil + nom qatorlari
def yn_compose(row: dict) -> str:
    y, n = _ws(row.get("year")), _ws(row.get("name"))
    if y and n:
        return f"{y} й. {n}"
    return n or y


def yn_split(s: str) -> dict:
    m = re.match(r"^\s*(\d{4})\s*(?:йил|йй?\.?)?\s*[,.\-–—]?\s*(.*)$", s or "")
    return {"year": m.group(1), "name": m.group(2)} if m else {"year": "", "name": _ws(s)}


# ---------------------------------------------------------------- umumiy
def web_to_person(w: dict) -> dict:
    p = {k: str(w.get(k, "") or "") for k in core.SIMPLE_FIELDS}
    js = job_since_compose(w.get("job_date", "")) if w.get("job_date") else ""
    if js:
        p["job_since"] = js
    elif w.get("job_date"):
        p["job_since"] = ""            # noto'g'ri kiritilgan sana: bo'sh (ogohlantirish beriladi)
    else:
        p["job_since"] = str(w.get("job_since", "") or "")   # fayldan o'qilgan, lekin sanaga ajralmagan matn
    p["birth_date"] = date_norm(p["birth_date"])
    if "langs" in w or "langs_other" in w:
        p["languages"] = langs_compose(w.get("langs"), w.get("langs_other", ""))
    p["graduated"] = [s for s in (yn_compose(r) for r in w.get("graduated", [])) if s]
    aw = [s for s in (yn_compose(r) for r in w.get("award_rows", [])) if s]
    if "award_rows" in w:
        p["awards"] = "; ".join(aw)

    def rows(lst):
        out = []
        for r in lst or []:
            text, per = str(r.get("text", "") or "").strip(), period_compose(r)
            if text or per:
                out.append([per, text])
        out.sort(key=lambda x: bool(re.search(r"ҳ\.в\.\s*$", x[0] or "")))   # "ҳ.в." doim eng oxirida (barqaror saralash)
        return out

    p["deputy"] = rows(w.get("deputy"))
    p["work"] = rows(w.get("work"))
    p["relatives"] = [rel_from_web(r) for r in w.get("relatives", [])
                      if _ws(r.get("relation")) or _ws(r.get("fio"))]
    return p


def person_to_web(p: dict) -> dict:
    w = {k: p.get(k, "") or "" for k in core.SIMPLE_FIELDS}
    w["job_date"] = job_since_split(w["job_since"])
    w["langs"], w["langs_other"] = langs_split(w["languages"])
    w["graduated"] = [yn_split(g) for g in p.get("graduated", [])]
    aw = _ws(p.get("awards"))
    w["award_rows"] = [] if not aw or aw.lower().rstrip(".") == core.NONE_WORD else \
        [yn_split(x) for x in re.split(r"\s*;\s*", aw) if x]

    def rows(lst):
        return [{**period_decompose(a), "text": b} for a, b in lst]

    w["deputy"] = rows(p.get("deputy", []))
    w["work"] = rows(p.get("work", []))
    w["relatives"] = [rel_to_web(r) for r in p.get("relatives", [])]
    return w


def warnings_json(ws):
    return [{"where": a, "msg": b} for a, b in ws]


# ---------------------------------------------------------------- ogohlantirish -> maydon
_SIMPLE_WHERE = {
    "F.I.Sh.": (0, "#fio"), "Жорий лавозими": (0, "#position"), "Жорий лавозим": (0, "#position"),
    "Туғилган йили": (1, "#birth_date"), "Туғилган жойи": (1, "#birth_place"), "Миллати": (1, "#nationality"),
    "Маълумоти": (1, "#education"), "Мутахассислиги": (1, "#specialty"), "Чет тиллари": (1, "#langs_other"),
    "Мукофотлар": (2, "#award-rows .n"), "Тамомлаган": (2, "#grad-rows .n"),
}


def locate(std: dict, where: str, msg: str, kept_work: list, kept_dep: list) -> dict | None:
    """Ogohlantirish qaysi maydonga tegishli ekanini qaytaradi (saytda bosilganda o'sha joyga o'tish uchun)."""
    if where in _SIMPLE_WHERE:
        st, sel = _SIMPLE_WHERE[where]
        return {"step": st, "sel": sel}
    if where == "Яқин қариндошлар":
        return {"step": 4, "sel": "#rel-quick"}

    def row_of(lst, kept, period=None, start=None):
        for i, (a, _t) in enumerate(lst):
            if period is not None and a == period:
                return kept[i] if i < len(kept) else None
            if start is not None:
                m = re.match(r"(\d{4})", a)
                if m and m.group(1) == str(start):
                    return kept[i] if i < len(kept) else None
        return None

    if where.startswith("Депутатлик "):
        i = row_of(std.get("deputy", []), kept_dep, period=where[len("Депутатлик "):])
        return {"step": 2, "list": "deputy", "idx": i} if i is not None else {"step": 2, "sel": "#deputy-rows .a"}
    if where.startswith("Меҳнат фаолияти"):
        work = std.get("work", [])
        i = None
        per = where[len("Меҳнат фаолияти"):].strip()
        if per:
            i = row_of(work, kept_work, period=per)
        if i is None:
            m = re.search(r"«([^»]+)»", msg)
            if m:
                i = row_of(work, kept_work, period=m.group(1))
        if i is None:
            m = re.match(r"(\d{4}) ва (\d{4}) йиллар", msg)
            if m:
                i = row_of(work, kept_work, start=m.group(2))
        if i is None:
            m = re.match(r"(.+?): давр олдингиси", msg)
            if m:
                i = row_of(work, kept_work, period=m.group(1))
        if i is None and msg.startswith("ёзувлар"):
            return {"step": 3, "sel": "#work-rows .a"}
        return {"step": 3, "list": "work", "idx": i} if i is not None else {"step": 3, "sel": "#work-rows .t"}
    m = re.match(r"^(.+?) \((.*)\)$", where)
    if m:
        fio = "" if m.group(2) == "исмсиз" else m.group(2)
        return {"step": 4, "rel": {"relation": m.group(1), "fio": fio}}
    return None

"""Standartlash, tekshiruv va oyna bilan ishlash uchun matn <-> ma'lumot almashtirish.

GUI shu modulga tayanadi, shuning uchun bu yerdagi hamma narsa oynasiz sinab ko'riladi.
"""
from __future__ import annotations

import re

from obj_parser import (REL_ORDER, canon_relation, parse_history,
                        parse_relatives_lines)

NONE_WORD = "йўқ"
OPTIONAL_DEFAULT_NONE = ("party", "military", "degree", "title", "awards")

MONTHS = {  # kirill oy nomlari -> raqam (ildiz bo'yicha)
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "май": 5, "июн": 6,
    "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}


def _ws(s) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# --------------------------------------------------------------- standartlash
def _fix_period(period: str) -> str:
    """Davr yozuvini namunadagi ko'rinishga keltiradi: 1977-1982 йй. / 2014 й. - ҳ.в.
    Qabul qiladi: 1995-2008, 1995 2008, 1995–2008 йй, 2024-, 2024 х.в., 2024 ҳ.в. va h.k."""
    p = _ws(period)
    if not p:
        return p
    p = p.replace("x", "х").replace("X", "Х")                 # lotin x -> kirill х
    p = re.sub(r"[–—−]", "-", p)
    p = re.sub(r"(?<![А-Яа-яЎўҚқҒғҲҳ])[хҳХҲ]\.?\s*в\.?", "ҳ.в.", p)
    present = "ҳ.в." in p
    years = re.findall(r"(?<!\d)\d{4}(?!\d)", p)
    rest = re.sub(r"(?<!\d)\d{4}(?!\d)|ҳ\.в\.|йй?\.?|[\s\-.,]", "", p, flags=re.I)
    if rest or not years or len(years) > 2:
        return p                                              # tushunilmadi: tegmaymiz
    if present or (len(years) == 1 and re.search(r"-\s*$", p)):
        return f"{years[0]} й.  -  ҳ.в."
    if len(years) == 2:
        a, b = years
        return f"{a}-{b} йй."
    return f"{years[0]} й."


def _fix_date(s: str) -> str:
    """'1959 йил 25 октябрь' / '25.10.1959' / '25-10-1959' -> 25.10.1959."""
    t = _ws(s)
    m = re.fullmatch(r"(\d{1,2})[.\-/ ](\d{1,2})[.\-/ ](\d{4})\s*(?:й\.?|йил)?", t)
    if m:
        return f"{int(m.group(1)):02d}.{int(m.group(2)):02d}.{m.group(3)}"
    m = re.fullmatch(r"(\d{4})\s*(?:й\.?|йил)\s*(\d{1,2})\s+([А-Яа-яЎўҚқҒғҲҳ]+)", t)
    if m:
        for root, num in MONTHS.items():
            if m.group(3).lower().startswith(root):
                return f"{int(m.group(2)):02d}.{num:02d}.{m.group(1)}"
    m = re.fullmatch(r"(\d{1,2})\s+([А-Яа-яЎўҚқҒғҲҳ]+)\s+(\d{4})\s*(?:й\.?|йил)?", t)
    if m:
        for root, num in MONTHS.items():
            if m.group(2).lower().startswith(root):
                return f"{int(m.group(1)):02d}.{num:02d}.{m.group(3)}"
    return t


def _title_case_name(fio: str) -> str:
    fio = _ws(fio)
    if fio and (fio == fio.upper() or fio == fio.lower()):
        return " ".join(w.capitalize() for w in fio.split(" "))
    return fio


def standardize(p: dict) -> dict:
    """Ma'lumotni qolipga solish: bo'shliqlar, davr yozuvi, sana, 'йўқ' qiymatlari."""
    q = dict(p)
    for k in ("job_since", "position", "birth_place", "nationality", "party", "education",
              "specialty", "degree", "title", "languages", "military", "awards"):
        q[k] = _ws(q.get(k))
    q["fio"] = _title_case_name(q.get("fio", ""))
    q["birth_date"] = _fix_date(q.get("birth_date", ""))
    # chet tillari: eski shakldagi "Малака даражаси:" so'zini olib tashlaymiz
    q["languages"] = _ws(re.sub(r"^\s*малака\s+даражаси\s*:?\s*", "", q.get("languages", ""), flags=re.I))
    # "рус тилини 2-даражали хизматчи, инглиз тилини ..." -> "рус, инглиз тиллари" (даража ёзилмайди)
    langs = re.findall(r"([А-Яа-яЎўҚқҒғҲҳ]+)\s+тилини", q["languages"])
    if langs:
        q["languages"] = f"{langs[0]} тили" if len(langs) == 1 else ", ".join(langs) + " тиллари"
        q["languages_fixed"] = True
    # idoraviy mukofotlar standartda alohida qator emas: davlat mukofotlari qatoriga qo'shamiz
    dept = _ws(q.pop("dept_awards", ""))
    q["awards_merged"] = False
    if dept and dept.lower().rstrip(".") != NONE_WORD:
        cur = _ws(q.get("awards"))
        q["awards"] = dept if (not cur or cur.lower().rstrip(".") == NONE_WORD) else f"{cur}; {dept}"
        q["awards_merged"] = True
    for k in OPTIONAL_DEFAULT_NONE:
        if not q.get(k):
            q[k] = NONE_WORD
    if q.get("job_since") and not q["job_since"].endswith(":"):
        q["job_since"] += ":"
    q["graduated"] = [_ws(g) for g in q.get("graduated", []) if _ws(g)]
    q["deputy"] = [[_fix_period(a), _ws(b)] for a, b in q.get("deputy", [])]
    q["work"] = [[_fix_period(a), _ws(b)] for a, b in q.get("work", [])]
    rels = []
    for r in q.get("relatives", []):
        r = dict(r)
        for k in ("relation", "fio", "birth", "work", "residence"):
            r[k] = _ws(r.get(k))
        if r["relation"]:
            r["relation"] = canon_relation(r["relation"])
            r["relation"] = r["relation"][0].upper() + r["relation"][1:]
        r["fio"] = _title_case_name(r["fio"])
        if re.search(r"вафот\s+этган", r["work"], re.I):
            r["deceased"] = True
        rels.append(r)
    # namunadagi tartib: ota-ona, aka-opa-uka-singil, turmush o'rtog'i, farzandlar, qaynota-qaynona
    rank = {name: n for n, name in enumerate(REL_ORDER)}
    rels.sort(key=lambda r: rank.get(r["relation"], len(rank)))
    q["relatives"] = rels
    return q


# ------------------------------------------------------------------ tekshiruv
_ABBR = re.compile(r"(?<!\w)(вил|тум|ш|тош|сам|респ|обл|ул|к|кв|д)\.(?!\w)", re.I)
_INITIALS = re.compile(r"(?<!\w)[А-ЯЎҚҒҲ]\.\s*[А-ЯЎҚҒҲ]\.|\s[А-ЯЎҚҒҲ]\.(?!\w)|(?<!\w)[а-яўқғҳ]\.[а-яўқғҳ]\.?(?!\w)")
_ACRONYM = re.compile(r"(?<!\w)(?:[А-ЯЎҚҒҲ]{2,6}|[А-ЯЎҚҒҲ][а-яўқғҳ]{1,4}[А-ЯЎҚҒҲ]{2,})(?!\w)")  # МТП, БухДУ
_BAD_RELATION = {"ўғлим", "қизим", "рафиқам", "турмуш ўртоғим", "акам", "укам", "опам",
                 "синглим", "отам", "онам", "умр йўлдошим", "хотиним", "эрим"}
_PLACE_OK_WORDS = ("вилояти", "шаҳри", "Қорақалпоғистон", "Республикаси")


def _year_range(period: str):
    m = re.match(r"(\d{4})(?:-(\d{4}|ҳ\.в\.))?", period)
    if not m:
        return None
    a = int(m.group(1))
    b = m.group(2)
    end = 9999 if b == "ҳ.в." else int(b) if b else a
    if "ҳ.в." in period:
        end = 9999
    return a, end


def _place_ok(s: str) -> bool:
    return ("вилояти" in s and ("тумани" in s or "шаҳри" in s)) or "шаҳри" in s or "Қорақалпоғистон" in s


def check(p: dict) -> list[tuple[str, str]]:
    """Namunadagi 'Изоҳ' qoidalari bo'yicha ogohlantirishlar: [(joy, xabar), ...]."""
    w: list[tuple[str, str]] = []

    def add(where, msg):
        w.append((where, msg))

    fio = p.get("fio", "")
    if len(fio.split()) < 3:
        add("F.I.Sh.", "Ф.И.Ш. тўлиқ (фамилия, исм, шариф) бўлиши керак")
    labels = {"birth_date": "Туғилган йили", "birth_place": "Туғилган жойи",
              "nationality": "Миллати", "education": "Маълумоти", "specialty": "Мутахассислиги",
              "position": "Жорий лавозими"}
    for k, name in labels.items():
        if not p.get(k):
            add(name, "тўлдирилмаган")
    if p.get("birth_date") and not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", p["birth_date"]):
        add("Туғилган йили", "сана КК.ОО.ЙЙЙЙ шаклида бўлиши керак")
    if p.get("awards_merged"):
        add("Мукофотлар", "«Идоравий мукофотлар» «Давлат мукофотлари» қаторига қўшилди — стандартда фақат давлат мукофотлари кўрсатилади, текширинг")
    if p.get("languages_fixed"):
        add("Чет тиллари", "даража олиб ташланди (фақат мукаммал билинадиган тиллар ёзилади) — текширинг")
    elif re.search(r"даражали|тилини|даража", p.get("languages", ""), re.I):
        add("Чет тиллари", "фақат тил номлари ёзилади: «рус, инглиз тиллари» (даража ёзилмайди)")
    if p.get("birth_place") and not _place_ok(p["birth_place"]):
        add("Туғилган жойи", "вилоят ва туман (шаҳар) тўлиқ кўрсатилиши керак")
    if not p.get("graduated"):
        add("Тамомлаган", "тамомлаган ўқув юрти кўрсатилмаган")
    if not p.get("work"):
        add("Меҳнат фаолияти", "ёзувлар топилмади")

    # qisqartmalar (шахсий + меҳнат)
    texts = [("Жорий лавозим", p.get("position", "")), ("Тамомлаган", " ".join(p.get("graduated", [])))]
    texts += [("Меҳнат фаолияти " + a, b) for a, b in p.get("work", [])]
    texts += [("Депутатлик " + a, b) for a, b in p.get("deputy", [])]
    for where, t in texts:
        if _ABBR.search(t) or _INITIALS.search(" " + t) or _ACRONYM.search(t):
            add(where, "қисқартма бор — тўлиқ ёзилиши керак")

    for k, (a, _t) in enumerate(p.get("work", [])[:-1]):
        if "ҳ.в." in a:
            add("Меҳнат фаолияти", f"«{a}» — «ҳ.в.» фақат охирги ёзувда бўлади")
    # меҳнат фаолияти ораси
    spans = [(r, _year_range(a)) for a, r in p.get("work", [])]
    prev_end = None
    for (txt, rng), (a, _) in zip(spans, p.get("work", [])):
        if not rng:
            add("Меҳнат фаолияти", f"давр аниқланмади: «{a or txt[:25]}»")
            continue
        if prev_end is not None and prev_end != 9999:
            if rng[0] - prev_end > 1:
                add("Меҳнат фаолияти", f"{prev_end} ва {rng[0]} йиллар орасида бўшлиқ бор")
            elif rng[0] < prev_end:
                add("Меҳнат фаолияти", f"{a}: давр олдингиси билан кесишади")
        prev_end = rng[1]

    # яқин қариндошлар
    rels = p.get("relatives", [])
    if not rels:
        add("Яқин қариндошлар", "жадвал топилмади")
    for r in rels:
        who = f"{r.get('relation') or '?'} ({r.get('fio') or 'исмсиз'})"
        if r.get("auto"):
            add(who, "матндан автоматик ажратилди — маълумотларни текширинг")
        if not r.get("relation"):
            add(who, "қариндошлиги аниқланмади")
        if r.get("relation", "").lower() in _BAD_RELATION:
            add(who, "қариндошлик «Ўғли», «Рафиқа»… эмас, «Ўғли/Қизи/Турмуш ўртоғи» шаклида ёзилади")
        if len(r.get("fio", "").split()) < 3 and "(" not in r.get("fio", ""):
            add(who, "Ф.И.Ш. тўлиқ эмас")
        if _INITIALS.search(" " + r.get("fio", "")):
            add(who, "Ф.И.Ш. да бош ҳарф билан қисқартма бор")
        if not re.match(r"\d{4} йил", r.get("birth", "")):
            add(who, "туғилган йили «1976 йил, …» шаклида бўлиши керак")
        elif not _place_ok(r["birth"]):
            add(who, "туғилган жойи: вилоят ва туман (шаҳар) тўлиқ кўрсатилиши керак")
        wk = r.get("work", "")
        if re.search(r"вафот", wk, re.I):
            if not re.match(r"\d{4} йил вафот этган", wk):
                add(who, "«2000 йил вафот этган (аввалги лавозими)» шаклида ёзилсин")
            elif "(" not in wk:
                add(who, "вафот этган бўлса, аввалги лавозими қавсда кўрсатилсин")
        elif re.match(r"Пенсияда", wk):
            if "(" not in wk:
                add(who, "пенсияда бўлса, аввалги лавозими қавсда кўрсатилсин")
            if re.search(r"илгари|бўлган", wk, re.I):
                add(who, "«илгари», «бўлган» сўзлари ёзилмайди")
        elif not wk:
            add(who, "иш жойи ва лавозими кўрсатилмаган")
        if _ABBR.search(wk) or _INITIALS.search(" " + wk) or _ACRONYM.search(wk):
            add(who, "иш жойида қисқартма бор — тўлиқ ёзилсин")
        if not r.get("deceased"):
            res = r.get("residence", "")
            if not res:
                add(who, "турар жойи кўрсатилмаган")
            elif not _place_ok(res) or _ABBR.search(res):
                add(who, "турар жойида вилоят, шаҳар, туман номлари тўлиқ кўрсатилсин")
    return w


# ------------------------------------------------- oyna <-> ma'lumot (matn)
SIMPLE_FIELDS = ["fio", "job_since", "position", "birth_date", "birth_place", "nationality",
                 "party", "education", "specialty", "degree", "title", "languages",
                 "military", "awards"]


def history_to_text(items) -> str:
    return "\n".join(f"{a} - {b}" if a else b for a, b in items)


def relatives_to_text(rels) -> str:
    lines = []
    for r in rels:
        parts = [r.get("relation", ""), r.get("fio", ""), r.get("birth", ""), r.get("work", "")]
        if not r.get("deceased"):
            parts.append(r.get("residence", ""))
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def text_to_relatives(text: str) -> list[dict]:
    """Qarindoshlar matni: har qator '|' yoki TAB bilan ajratilgan, yoki erkin yozilgan bo'lishi mumkin
    (Word jadvalidan nusxalab joylash ham ishlaydi)."""
    rels: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        seps = "|" if "|" in line else ("\t" if "\t" in line else None)
        if seps:
            cells = [_ws(c) for c in line.split(seps)]
            cells = [c for c in cells] + [""] * max(0, 3 - len(cells))
            rel = {"relation": cells[0], "fio": cells[1], "birth": cells[2],
                   "work": cells[3] if len(cells) > 3 else "",
                   "residence": " ".join(c for c in cells[4:] if c)}
            if re.search(r"вафот", rel["work"], re.I) and not rel["residence"]:
                rel["deceased"] = True
        else:
            got = parse_relatives_lines([line])
            rel = got[0] if got else {"relation": "", "fio": _ws(line), "birth": "", "work": "",
                                      "residence": "", "auto": True}
        rels.append(rel)
    return rels


RELATION_CHOICES = ["Отаси", "Онаси", "Акаси", "Опаси", "Укаси", "Синглиси", "Турмуш ўртоғи",
                    "Ўғли", "Қизи", "Қайнотаси", "Қайнонаси"]


def make_relative(relation, fio, birth_year, birth_place, status, work="", residence="", death_year=""):
    """«Qarindosh qo'shish» oynasi uchun: maydonlardan namunaviy yozuv yasaydi.
    status: 'works' (ishlaydi) | 'pension' (pensiyada) | 'dead' (vafot etgan)."""
    work, residence = _ws(work), _ws(residence)
    birth = f"{_ws(birth_year)} йил" + (f", {_ws(birth_place)}" if _ws(birth_place) else "")
    rel = {"relation": canon_relation(relation), "fio": _ws(fio), "birth": birth}
    if status == "pension":
        rel["work"] = f"Пенсияда ({work})" if work else "Пенсияда"
        rel["residence"] = residence
    elif status == "dead":
        y = _ws(death_year)
        rel["work"] = (f"{y} йил вафот этган" if y else "вафот этган") + (f" ({work})" if work else "")
        rel["residence"] = ""
        rel["deceased"] = True
    else:
        rel["work"] = work
        rel["residence"] = residence
    return rel


def person_to_form(p: dict) -> dict:
    f = {k: p.get(k, "") or "" for k in SIMPLE_FIELDS}
    f["graduated"] = "\n".join(p.get("graduated", []))
    f["deputy"] = history_to_text(p.get("deputy", []))
    f["work"] = history_to_text(p.get("work", []))
    f["relatives"] = relatives_to_text(p.get("relatives", []))
    return f


def form_to_person(f: dict) -> dict:
    p = {k: _ws(f.get(k, "")) for k in SIMPLE_FIELDS}
    p["graduated"] = [_ws(x) for x in f.get("graduated", "").splitlines() if _ws(x)]
    p["deputy"] = parse_history(f.get("deputy", "").splitlines())
    if len(p["deputy"]) == 1 and re.fullmatch(r"йўқ\.?", p["deputy"][0][1], re.I) and not p["deputy"][0][0]:
        p["deputy"] = []
    p["work"] = parse_history(f.get("work", "").splitlines())
    p["relatives"] = text_to_relatives(f.get("relatives", ""))
    return standardize(p)


# ------------------------------------------------------------------- rasm
def prepare_photo(path: str, out_path: str) -> str:
    """Rasmni 3:4 nisbatga markazdan qirqadi (cho'zilib ketmasligi uchun)."""
    try:
        from PIL import Image
    except ImportError:
        return path
    im = Image.open(path).convert("RGB")
    w, h = im.size
    target = 3 / 4
    if w / h > target:      # juda keng -> yon tomonlarni qirqamiz
        nw = int(h * target)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:                   # juda baland -> tepa/pastni qirqamiz (yuz tepada bo'ladi)
        nh = int(w / target)
        top = max(0, int((h - nh) * 0.25))
        im = im.crop((0, top, w, top + nh))
    im = im.resize((600, 800))
    im.save(out_path, "JPEG", quality=92)
    return out_path

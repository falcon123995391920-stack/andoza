"""Eski obyektivkani o'qib, maydonlarga ajratadi (qoidalarga asoslangan, oflayn).

Kirish: .docx fayl yoki oddiy matn. Chiqish: builder.build() kutadigan dict.
Maydon nomlari (yorliqlar) bo'yicha ishlaydi, shuning uchun yorliqlari namunadagidek
bo'lgan hujjatlarda yaxshi ishlaydi. Boshqa ko'rinishlar uchun namunalar kerak.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

# maydon -> yorliq regex (colon bilan). Tartib muhim emas.
LABEL_RES = {
    "birth_date":  r"туғилган\s+йили\s*:",
    "birth_place": r"туғилган\s+жойи\s*:",
    "nationality": r"миллати\s*:",
    "party":       r"партиявийлиги\s*:",
    "education":   r"маълумоти\s*:",
    "graduated":   r"тамомлаган\s*:",
    "specialty":   r"маълумоти\s+бўйича\s+мутахассислиги\s*:",
    "degree":      r"илмий\s+даражаси\s*:",
    "title":       r"илмий\s+унвони\s*:",
    "languages":   r"қайси\s+чет\s+тилларини\s+билади\s*:",
    "military":    r"ҳарбий\s*\(махсус\)\s+унвони\s*:",
    "awards":      r"давлат\s+мукофотлари\s+билан\s+тақдирланганми\s*\(қанақа\)\s*:",
    "dept_awards": r"идоравий\s+мукофотлар\s+билан\s+тақдирланганми\s*\(қанақа\)\s*:",
    "deputy":      r"халқ\s+депутатлари.*?\(тўлиқ\s+кўрсатилиши\s+лозим\)\s*:",
}
_LABEL_COMPILED = {k: re.compile(v, re.I | re.S) for k, v in LABEL_RES.items()}
HEAD_WORK = re.compile(r"меҳнат\s+фаолияти", re.I)
HEAD_REL = re.compile(r"яқин\s+қариндошлари|^\s*маълумот\s*$", re.I)
HEAD_NOTE = re.compile(r"^\s*изоҳ\s*:?\s*$", re.I)
HEAD_MAIN = re.compile(r"^\s*маълумотнома\s*$", re.I)

_PERIOD = re.compile(
    r"^\s*((?:\d{4}\s*[-–—]\s*(?:\d{4}|ҳ\.?\s*в\.?)|\d{4})"
    r"\s*(?:йй?\.?)?(?:\s*[-–—]?\s*ҳ\.?\s*в\.?)?)\s*(?:[-–—:]\s*)?(.*)$",
    re.S,
)


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ----------------------------------------------------------- tarix qatorlari
def parse_history(lines: list[str]) -> list[list[str]]:
    """['1977-1982 йй. - ...', ...] -> [[davr, matn], ...]. Davri yo'q qator oldingisiga qo'shiladi."""
    items: list[list[str]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = _PERIOD.match(line)
        if m and m.group(2).strip():
            items.append([_ws(m.group(1)), _ws(m.group(2))])
        elif items:
            items[-1][1] = _ws(items[-1][1] + " " + line)
        else:
            items.append(["", _ws(line)])
    return items


# ------------------------------------------------------------- hujjatni o'qish
def _iter_blocks(doc):
    """Hujjat tanasidagi paragraf va jadvallarni tartibda beradi."""
    for el in doc.element.body.iterchildren():
        tag = el.tag.split("}")[1]
        if tag == "p":
            yield Paragraph(el, doc)
        elif tag == "tbl":
            yield Table(el, doc)


def _table_to_lines(tbl: Table) -> list[str]:
    """Maydonlar jadvali (yorliq | qiymat ustunlari) -> tab bilan ajratilgan qatorlar,
    xuddi oddiy paragraflardagi 'Yorliq:<TAB>Yorliq2:' / 'qiymat<TAB>qiymat2' shaklidek."""
    out: list[str] = []
    for row in tbl.rows:
        uniq, cols = [], []
        for cell in row.cells:
            if any(cell._tc is u._tc for u in uniq):
                continue
            uniq.append(cell)
            cols.append([p.text.replace("\n", " ").strip() for p in cell.paragraphs])
        depth = max((len(c) for c in cols), default=0)
        for k in range(depth):
            out.append("\t".join(c[k] if k < len(c) else "" for c in cols).rstrip())
    return out


def _is_fields_table(tbl: Table) -> bool:
    """Birinchi qatordagi kataklardan birida maydon yorlig'i bo'lsa, bu maydonlar jadvali."""
    if not tbl.rows:
        return False
    return any(_labels_in(c.text) for c in tbl.rows[0].cells)


def _docx_to_lines_and_tables(path: str):
    doc = Document(path)
    lines: list[str] = []
    tables: list[Table] = []
    for b in _iter_blocks(doc):
        if isinstance(b, Paragraph):
            for part in b.text.split("\n"):
                lines.append(part.rstrip())
        elif _is_fields_table(b):
            lines.extend(_table_to_lines(b))
        else:
            tables.append(b)
    return lines, tables


_SOFFICE_LOCK = threading.Lock()


def doc_to_docx(path: str) -> str:
    """Eski .doc ni .docx ga o'tkazadi (LibreOffice yoki Word orqali)."""
    out_dir = tempfile.mkdtemp(prefix="obj_")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        for cand in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                     r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
            if Path(cand).exists():
                soffice = cand
                break
    if soffice:
        with _SOFFICE_LOCK:
            subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir", out_dir, path],
                           capture_output=True, timeout=180)
        res = Path(out_dir) / (Path(path).stem + ".docx")
        if res.exists():
            return str(res)
    try:  # Windows + Microsoft Word
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        d = word.Documents.Open(str(Path(path).resolve()))
        res = str(Path(out_dir) / (Path(path).stem + ".docx"))
        d.SaveAs2(res, FileFormat=16)
        d.Close()
        word.Quit()
        return res
    except Exception:
        pass
    raise RuntimeError(
        ".doc faylni o'qib bo'lmadi. Faylni Word'da oching va "
        "«Boshqacha saqlash» orqali .docx qilib saqlang.")


# ------------------------------------------------------------ qarindoshlar
# (kanonik nom, variantlar) — tartib namunadagi tartib
REL_ORDER = ["Отаси", "Онаси", "Акаси", "Опаси", "Укаси", "Синглиси", "Турмуш ўртоғи",
             "Ўғли", "Қизи", "Қайнотаси", "Қайнонаси"]
_REL_VARIANTS = {
    "Отаси": ["отаси", "отам", "ота"], "Онаси": ["онаси", "онам", "она"],
    "Акаси": ["акаси", "акам", "ака"], "Опаси": ["опаси", "опам", "опа"], "Укаси": ["укаси", "укам", "ука"],
    "Синглиси": ["синглиси", "синглим", "сингил", "сингли"],
    "Турмуш ўртоғи": ["турмуш\\s+ўртоғи", "турмуш\\s+ўртоги", "рафиқаси", "умр\\s+йўлдоши",
                      "хотини", "эри", "рафиқам", "турмуш\\s+ўртоғим", "умр\\s+йўлдошим", "хотиним", "эрим"],
    "Ўғли": ["ўғли", "ўғлим", "угли"], "Қизи": ["қизи", "қизим", "кизи"],
    "Қайнотаси": ["қайнотаси", "қайин\\s*ота", "қайинотаси"],
    "Қайнонаси": ["қайнонаси", "қайин\\s*она", "қайиноаси"],
    "Ўгай отаси": ["ўгай\\s+отаси"], "Ўгай онаси": ["ўгай\\s+онаси"],
}
_REL_ALT = "|".join(sorted((v for vs in _REL_VARIANTS.values() for v in vs), key=len, reverse=True))
_REL_START = re.compile(r"^\s*(?:\d+\s*[.)]\s*)?(" + _REL_ALT + r")(?![а-яўқғҳА-ЯЎҚҒҲ])\s*[-–—:.)]?\s*", re.I)


def canon_relation(text: str) -> str:
    t = _ws(text).strip(" -–—:.").lower()
    for canon, variants in _REL_VARIANTS.items():
        if any(re.fullmatch(v, t, re.I) for v in variants):
            return canon
    return _ws(text)


_ADDR_END = re.compile(r"(вилояти|тумани|шаҳри|шаҳар|қишлоғи|маҳалласи|маҳалла|кўчаси|даҳаси|мавзеси|"
                       r"массиви|йиғини|шаҳарчаси|посёлкаси|МФЙ|ҚФЙ|ШФЙ|ФЙ)$", re.I)
_ADDR_NUM = re.compile(r"^(?:\d+\s*[-]?\s*(?:уй|хонадон|квартира)|(?:уй|хонадон)\s*\d+)$", re.I)


def _split_commas(s: str) -> list[str]:
    """Vergul bo'yicha bo'ladi, lekin qavs va qo'shtirnoq ichidagisini bo'lmaydi."""
    out, buf, depth, q = [], [], 0, False
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif ch in '"“”«»':
            q = not q
        if ch in ",;" and depth == 0 and not q:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return [t for t in out if t]


def _is_addr(tok: str) -> bool:
    return bool(_ADDR_END.search(tok.strip()) or _ADDR_NUM.match(tok.strip()))


def _split_free(rest: str):
    """Erkin matn: 'Ф.И.Ш. 1950 йил, Вилоят, Туман, Иш жойи, Турар жoйи' -> (fio, birth, work, residence)."""
    rest = _ws(rest)
    m = re.search(r"(?<!\d)(1[89]\d\d|20[0-2]\d)(?!\d)", rest)
    if not m:
        return None
    fio = rest[: m.start()].strip(" ,;-–—:")
    year = m.group(1)
    tail = re.sub(r"^\s*(?:йилда|йил|й\.?)?\s*[,;]?", "", rest[m.end():]).strip(" ,;")
    toks = _split_commas(tail)
    place, i = [], 0
    while i < len(toks) and len(place) < 3:
        if re.match(r"^(Пенсияда|\d{4}\s*йил\s+вафот|вафот)", toks[i], re.I):
            break
        place.append(toks[i])
        i += 1
        if re.search(r"(тумани|шаҳри|шаҳар)$", place[-1], re.I):
            break
    toks = toks[i:]
    dead = next((k for k, t in enumerate(toks) if re.search(r"вафот", t, re.I)), None)
    residence = []
    if dead is None:
        while toks and _is_addr(toks[-1]) and len(residence) < 5:
            residence.insert(0, toks.pop())
    work = ", ".join(toks)
    birth = f"{year} йил" + (", " + ", ".join(place) if place else "")
    return fio, birth, work, ", ".join(residence)


def _rel_from_parts(relation: str, parts: list[str]) -> dict:
    parts = [_ws(x) for x in parts]
    fio = parts[0] if len(parts) > 0 else ""
    birth = parts[1] if len(parts) > 1 else ""
    work = parts[2] if len(parts) > 2 else ""
    res = " ".join(parts[3:]) if len(parts) > 3 else ""
    rel = {"relation": canon_relation(relation), "fio": fio, "birth": birth, "work": work, "residence": res}
    if re.search(r"вафот", work, re.I) and not res:
        rel["deceased"] = True
    return rel


def parse_relatives_lines(lines: list[str]) -> list[dict]:
    """Matn (qatorlar) -> qarindoshlar. '|' yoki TAB bilan ajratilgan, yoki erkin matn."""
    items: list[str] = []
    for raw in lines:
        if HEAD_NOTE.match(raw):
            break
        if not raw.strip():
            continue
        if _REL_START.match(raw):
            items.append(raw.strip())
        elif items:
            items[-1] += " " + raw.strip()
    rels = []
    for it in items:
        m = _REL_START.match(it)
        rest = it[m.end():]
        if "|" in it or "\t" in it:
            seps = "|" if "|" in it else "\t"
            cells = [c for c in (x.strip() for x in it.split(seps))]
            relation, parts = cells[0], cells[1:]
            if relation and not _REL_START.match(relation + " "):
                relation = m.group(1)
            rel = _rel_from_parts(relation, parts)
        else:
            free = _split_free(rest)
            if free is None:
                rel = {"relation": canon_relation(m.group(1)), "fio": _ws(rest), "birth": "",
                       "work": "", "residence": "", "auto": True}
            else:
                rel = _rel_from_parts(m.group(1), list(free))
                rel["auto"] = True
        rels.append(rel)
    return rels


def parse_relatives_table(tbl: Table) -> list[dict]:
    """Jadval qatorlari: birinchi katak qarindoshlik so'zi bo'lgan qatorlar (sarlavhaga bog'liq emas)."""
    rels = []
    for row in tbl.rows:
        uniq, cells = [], []
        for cell in row.cells:           # birlashgan kataklar bir marta olinadi
            if any(cell._tc is u._tc for u in uniq):
                continue
            uniq.append(cell)
            cells.append(_ws(" ".join(p.text for p in cell.paragraphs)))
        if not cells or not _REL_START.match(cells[0] + " "):
            continue
        relation = cells[0]
        if len(cells) >= 4:
            rel = _rel_from_parts(relation, cells[1:])
        else:  # qisqa qator: erkin matn sifatida
            line = relation + " " + " ".join(cells[1:])
            rel = (parse_relatives_lines([line]) or [{"relation": canon_relation(relation), "fio": "",
                                                       "birth": "", "work": "", "residence": ""}])[0]
        rels.append(rel)
    return rels


# -------------------------------------------------------------- matndan
def _labels_in(line: str):
    found = []
    for field, rx in _LABEL_COMPILED.items():
        for m in rx.finditer(line):
            found.append((m.start(), m.end(), field))
    found.sort()
    # bir-birini qoplaganlarini olib tashlaymiz (uzunrog'i qoladi)
    res = []
    for f in found:
        if res and f[0] < res[-1][1]:
            if f[1] - f[0] > res[-1][1] - res[-1][0]:
                res[-1] = f
            continue
        res.append(f)
    return res


def parse_lines(lines: list[str]) -> dict:
    p: dict = {"graduated": [], "deputy": [], "work": [], "relatives": []}
    n = len(lines)
    i = 0

    # --- sarlavha: F.I.Sh., joriy ish joyi
    head: list[str] = []
    while i < n and not _labels_in(lines[i]) and not HEAD_WORK.search(lines[i]):
        if lines[i].strip() and not HEAD_MAIN.match(lines[i]):
            head.append(lines[i].strip())
        i += 1
    if head:
        p["fio"] = _ws(head[0])
        rest = head[1:]
        # sana va lavozim bir qatorda: "2021 йил 1 январдан: Тошкент ... ўринбосари"
        m_js = re.match(r"^\s*(\d{4}\s*йил[^:]{0,30}:)\s*(.+)$", rest[0]) if rest else None
        if m_js:
            p["job_since"] = _ws(m_js.group(1))
            rest = [m_js.group(2)] + rest[1:]
        elif rest and re.search(r"\d{4}\s*йил", rest[0]) and rest[0].rstrip().endswith(":"):
            p["job_since"] = _ws(rest[0])
            rest = rest[1:]
        p["position"] = _ws(" ".join(rest))

    def is_stop(s: str) -> bool:
        return bool(HEAD_WORK.search(s) or HEAD_REL.search(s) or HEAD_NOTE.match(s))

    # --- maydonlar
    while i < n:
        line = lines[i]
        if HEAD_WORK.search(line):
            break
        labs = _labels_in(line)
        if not labs:
            i += 1
            continue
        segs = []
        for k, (st, en, f) in enumerate(labs):
            nxt = labs[k + 1][0] if k + 1 < len(labs) else len(line)
            segs.append(line[en:nxt].strip(" \t"))
        if any(segs):
            # bir qatorda yorliq va qiymat (ba'zan bir nechta yorliq ketma-ket): "Yorliq: qiymat Yorliq2: qiymat2"
            vals = [[sg] if sg else [] for sg in segs]
            i += 1
            while i < n and not _labels_in(lines[i]) and not is_stop(lines[i]):
                if lines[i].strip():
                    vals[-1].append(lines[i].strip())
                i += 1
            for (st, en, f), v in zip(labs, vals):
                _store(p, f, v)
        elif len(labs) == 1:
            field = labs[0][2]
            vals = []
            i += 1
            while i < n and not _labels_in(lines[i]) and not is_stop(lines[i]):
                if lines[i].strip():
                    vals.append(lines[i].strip())
                i += 1
            _store(p, field, vals)
        else:  # juftlik: qiymatlar keyingi qatorlarda, tab bilan ajratilgan
            fields = [f for _, _, f in labs]
            cols: list[list[str]] = [[] for _ in fields]
            i += 1
            while i < n and not _labels_in(lines[i]) and not is_stop(lines[i]):
                if lines[i].strip():
                    parts = re.split(r"\t+|\s{3,}", lines[i].rstrip())
                    if lines[i].startswith("\t"):
                        parts = parts[1:] if parts and parts[0] == "" else parts
                        if len(parts) == 1 and len(fields) >= 2:
                            parts = [""] * (len(fields) - 1) + parts
                    for j, part in enumerate(parts[: len(fields)]):
                        if part.strip():
                            cols[j].append(part.strip())
                i += 1
            for f, v in zip(fields, cols):
                _store(p, f, v)

    # --- mehnat faoliyati
    if i < n and HEAD_WORK.search(lines[i]):
        i += 1
        work_lines = []
        while i < n and not is_stop(lines[i]):
            work_lines.append(lines[i])
            i += 1
        p["work"] = parse_history(work_lines)
    p["relatives"] = parse_relatives_lines(lines[i:])
    return p


def _store(p: dict, field: str, vals: list[str]):
    vals = [v for v in (_ws(v) for v in vals) if v]
    if field == "graduated":
        p["graduated"] = vals
    elif field == "deputy":
        txt = " ".join(vals)
        p["deputy"] = [] if re.fullmatch(r"йўқ\.?", txt, re.I) or not txt else parse_history(vals)
    else:
        p[field] = _ws(" ".join(vals))


# ---------------------------------------------------------------- ochiq API
def parse_docx(path: str) -> dict:
    lines, tables = _docx_to_lines_and_tables(path)
    p = parse_lines(lines)
    rels = []
    for t in tables:
        rels += parse_relatives_table(t)
    if rels:                      # jadval topilsa, u matndan ishonchliroq
        p["relatives"] = rels
    return p


def parse_file(path: str) -> dict:
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return parse_docx(path)
    if ext == ".doc":
        return parse_docx(doc_to_docx(path))
    if ext in (".txt",):
        return parse_lines(Path(path).read_text(encoding="utf8", errors="replace").splitlines())
    raise ValueError("Faqat .docx, .doc yoki .txt fayl tanlang")


def parse_text(text: str) -> dict:
    return parse_lines(text.splitlines())


# --------------------------------------------------------- rasm (tahrirlash uchun)
def extract_photo(docx_path: str):
    """Hujjatdagi birinchi 'odam rasmi'ga o'xshash (tik yoki kvadrat) rasmni bayt sifatida qaytaradi."""
    try:
        import io
        from PIL import Image
        doc = Document(docx_path)
        xml = doc.element.xml
        rids = re.findall(r'r:embed="([^"]+)"|r:id="([^"]+)"', xml)
        seen = []
        for a, b in rids:
            rid = a or b
            part = doc.part.related_parts.get(rid)
            if part is None or not getattr(part, "content_type", "").startswith("image/"):
                continue
            if part.content_type in ("image/jpeg", "image/png", "image/bmp", "image/gif", "image/tiff"):
                seen.append(part.blob)
        for blob in seen:
            try:
                w, h = Image.open(io.BytesIO(blob)).size
            except Exception:
                continue
            if w >= 60 and h >= 60 and h >= w * 0.9:
                return blob
        return None
    except Exception:
        return None


def load_file(path: str):
    """(person, photo_bytes|None). .doc avval .docx ga o'tkaziladi."""
    ext = Path(path).suffix.lower()
    if ext == ".doc":
        path = doc_to_docx(path)
        ext = ".docx"
    if ext == ".docx":
        return parse_docx(path), extract_photo(path)
    return parse_file(path), None

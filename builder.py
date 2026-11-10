"""Obyektivka (ma'lumotnoma) standart shablonini yasovchi.

Ma'lumot (dict) -> namunadagi 2 sahifali Word (.docx).
Format qiymatlari namuna .doc faylidan olingan.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Emu, Twips

import doclang

FONT = "Times New Roman"
BASE = 11
BIG = 14
TAB_COL2 = Twips(4320)          # ikkinchi ustun boshlanishi (7,62 sm)
WORK_HANG = Emu(942340)         # mehnat faoliyati osilgan chekinish (~2,6 sm)
REL_COLS = [1260, 2160, 1980, 2860, 2000]   # twips
REL_HEADERS = [
    "Қарин-\nдошлиги",
    "Фамилияси, исми\nва отасининг исми",
    "Туғилган йили\nва жойи",
    "Иш жойи ва лавозими",
    "Турар жойи",
]


# ---------------------------------------------------------------- yordamchilar
def _set_font(run, size=BASE, bold=None, italic=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), FONT)


def _para(doc_or_cell, align=None, before=0, after=0, left=None, first=None,
          right=None, tabs=(), keep_next=False):
    p = doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.0
    if align is not None:
        p.alignment = align
    if left is not None:
        pf.left_indent = left
    if first is not None:
        pf.first_line_indent = first
    if right is not None:
        pf.right_indent = right
    for t in tabs:
        pf.tab_stops.add_tab_stop(t)
    if keep_next:
        pf.keep_with_next = True
    return p


def _text(p, text, size=BASE, bold=None):
    """Matnni yozadi; '\\t' tab, '\\n' qator uzilishi sifatida ishlanadi."""
    parts = text.split("\n")
    for i, part in enumerate(parts):
        r = p.add_run(part)
        _set_font(r, size, bold)
        if i < len(parts) - 1:
            r.add_break()
    return p


def _tab(p, size=BASE):
    r = p.add_run("\t")
    _set_font(r, size)


def _cell_borders(cell, sz=4):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
        b.append(e)
    tcPr.append(b)


def _cell_text(cell, text, bold=False, wide=False):
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if wide:  # namunada 1-ustun matni katak chetiga 108 twips kengaytirilgan
        p.paragraph_format.left_indent = Twips(-108)
        p.paragraph_format.right_indent = Twips(-108)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    _text(p, text, BASE, bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _cell_borders(cell)


# ----------------------------------------------------------------------- rasm
def _add_floating_photo(paragraph, image_path, w_cm=3.0, h_cm=4.0, top_cm=1.5):
    """3x4 sm rasmni o'ng yuqori burchakka (matnga xalaqit bermay) qo'yadi."""
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Cm(w_cm), height=Cm(h_cm))
    inline = run._element.find(".//" + qn("wp:inline"))
    cx, cy = inline.find(qn("wp:extent")).get("cx"), inline.find(qn("wp:extent")).get("cy")
    doc_pr = inline.find(qn("wp:docPr"))
    cnv = inline.find(qn("wp:cNvGraphicFramePr"))
    graphic = inline.find(qn("a:graphic"))

    anchor = OxmlElement("wp:anchor")
    for k, v in dict(distT="0", distB="0", distL="0", distR="0", simplePos="0",
                     relativeHeight="251658240", behindDoc="0", locked="0",
                     layoutInCell="1", allowOverlap="1").items():
        anchor.set(k, v)
    sp = OxmlElement("wp:simplePos"); sp.set("x", "0"); sp.set("y", "0")
    ph = OxmlElement("wp:positionH"); ph.set("relativeFrom", "margin")
    al = OxmlElement("wp:align"); al.text = "right"; ph.append(al)
    pv = OxmlElement("wp:positionV"); pv.set("relativeFrom", "page")
    po = OxmlElement("wp:posOffset"); po.text = str(int(Cm(top_cm))); pv.append(po)
    ext = OxmlElement("wp:extent"); ext.set("cx", cx); ext.set("cy", cy)
    ee = OxmlElement("wp:effectExtent")
    for k in ("l", "t", "r", "b"):
        ee.set(k, "0")
    wrap = OxmlElement("wp:wrapNone")
    for el in (sp, ph, pv, ext, ee, wrap, doc_pr, cnv, graphic):
        anchor.append(el)
    drawing = inline.getparent()
    drawing.remove(inline)
    drawing.append(anchor)


# --------------------------------------------------------------------- asosiy
def _setup(doc):
    s = doc.sections[0]
    s.orientation = WD_ORIENT.PORTRAIT
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin, s.right_margin = Cm(2.0), Cm(1.0)
    s.top_margin, s.bottom_margin = Cm(1.5), Cm(1.0)
    s.header_distance = s.footer_distance = Cm(0)
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(BASE)
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    # Kelishuv bo'yicha matn tili: o'zbek (kirill)
    lang = OxmlElement("w:lang"); lang.set(qn("w:val"), "uz-Cyrl-UZ")
    rpr.append(lang)


# ----------------------------------------------- ikki ustunli maydonlar (jadvalsiz)
# Namunadagidek oddiy abzaslar: "Yorliq1:<TAB>Yorliq2:" va "qiymat1<TAB>qiymat2".
# Jadval ishlatilmaydi, shuning uchun Wordda jadval chegarasi, tutqichi yoki katak
# belgilari ko'rinmaydi. Ikkinchi ustun har doim 7,62 sm dan boshlanadi; uzun qiymat
# ikkinchi qatorga o'tsa ham shu chiziqdan boshlanadi (osilgan chekinish).
GAP_PT = 10          # birinchi ustun qiymati bilan ikkinchi ustun orasidagi xavfsiz bo'shliq
_FONT_FILES = {
    False: ["C:/Windows/Fonts/times.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/liberation/LiberationSerif-Regular.ttf", "/Library/Fonts/Times New Roman.ttf"],
    True:  ["C:/Windows/Fonts/timesbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/liberation/LiberationSerif-Bold.ttf", "/Library/Fonts/Times New Roman Bold.ttf"],
}
_font_cache: dict = {}


def _text_width_pt(text: str, bold: bool = False, size: float = BASE) -> float:
    """Matn kengligi (pt). Times New Roman bilan metrikasi bir xil shriftdan o'lchanadi;
    shrift topilmasa, ehtiyotkor taxmin (0,52 em harfiga) ishlatiladi."""
    if bold not in _font_cache:
        font = None
        try:
            from PIL import ImageFont
            for f in _FONT_FILES[bold]:
                if Path(f).exists():
                    font = ImageFont.truetype(f, 200)
                    break
        except Exception:   # noqa: BLE001
            font = None
        _font_cache[bold] = font
    font = _font_cache[bold]
    if font is None:
        return len(text) * size * 0.52
    return font.getlength(text) * size / 200.0


def _fits_col1(text: str) -> bool:
    return _text_width_pt(text or "") <= TAB_COL2.pt - GAP_PT


def _two_col_para(doc, left, right, left_bold=False, right_bold=False, before=0, right_indent=None):
    """Bitta abzas: chap matn, TAB, o'ng matn. O'ng matn uzun bo'lsa 2-ustun chizig'idan davom etadi."""
    p = _para(doc, before=before, left=TAB_COL2, first=-TAB_COL2, right=right_indent, tabs=[TAB_COL2])
    _text(p, left or "", bold=left_bold)
    _tab(p)
    _text(p, right or "", bold=right_bold)
    return p


def _pair_block(doc, l_lab, l_val, r_lab, r_vals, near_photo=False):
    """Ikki ustunli juftlik. Chap qiymat 1-ustunga sig'masa, ikki ustun o'rniga ketma-ket
    ikkita oddiy maydon sifatida yoziladi (shunda ham jadval ishlatilmaydi)."""
    ri = Cm(3.4) if near_photo else None
    r_vals = [v for v in (r_vals or [""])] or [""]
    if _fits_col1(l_val or ""):
        _two_col_para(doc, l_lab, r_lab, left_bold=True, right_bold=True, before=6, right_indent=ri)
        _two_col_para(doc, l_val, r_vals[0], before=0, right_indent=ri)
        for extra in r_vals[1:]:                      # 2-ustunning qo'shimcha qatorlari
            p = _para(doc, left=TAB_COL2, right=ri)
            _text(p, extra)
    else:
        p = _para(doc, before=6, right=ri); _text(p, l_lab, bold=True)
        p = _para(doc, right=ri); _text(p, l_val or "")
        p = _para(doc, before=6, right=ri); _text(p, r_lab, bold=True)
        for v in r_vals:
            p = _para(doc, right=ri); _text(p, v)


def _inline_block(doc, label, value):
    """'Yorliq:<TAB>qiymat' bir qatorda (ikkinchi ustun chizig'idan)."""
    _two_col_para(doc, label, value, left_bold=True, before=8)


def _single(doc, label, value):
    p = _para(doc, before=6)
    _text(p, label, bold=True)
    p = _para(doc)
    _text(p, value or "")


def _history(doc, items, hang=WORK_HANG, before=4):
    """'1977-1982 йй. -<TAB>matn': matn ustuni har doim bir chiziqda (ҳ.в. qatorlari ham)."""
    need = max([_text_width_pt(f"{p} -") for p, _ in items if p] + [0]) + 6
    if need > Emu(hang).pt:                      # uzunroq davr yozuvi (masalan, ingliz "present") — chekinish kengayadi
        hang = Pt(need)
    for period, text in items:
        p = _para(doc, before=before, left=hang, first=-hang, tabs=[hang])
        _text(p, f"{period} -\t{text}" if period else text)


def build(person: dict, out_path, photo_path=None, lang="cy"):
    L = doclang.LABELS[lang if lang in doclang.LABELS else "cy"]
    person = doclang.localize(person, lang)
    doc = Document()
    _setup(doc)
    body = doc.element.body
    # python-docx bo'sh hujjatdagi birinchi bo'sh paragrafni olib tashlaymiz
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)

    # --- sarlavha
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, right=Twips(1204))
    if photo_path:
        _add_floating_photo(p, photo_path)
    _text(p, L["title"], BIG, True)
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, before=16, right=Twips(1204))
    _text(p, person["fio"], BIG, True)

    # --- joriy ish joyi
    narrow = Cm(3.4)  # rasm joyiga yetib bormasligi uchun
    p = _para(doc, before=13, right=narrow)
    _text(p, person.get("job_since", ""))
    p = _para(doc, right=narrow)
    _text(p, person.get("position", ""), bold=True)

    # --- shaxsiy ma'lumotlar (ikki ustun, jadvalsiz: abzas + TAB)
    grads = person.get("graduated") or [""]
    _pair_block(doc, L["birth_date"], person.get("birth_date"),
                L["birth_place"], [person.get("birth_place")], near_photo=True)
    _pair_block(doc, L["nationality"], person.get("nationality"),
                L["party"], [person.get("party")])
    _pair_block(doc, L["education"], person.get("education"), L["graduated"], grads)
    _inline_block(doc, L["specialty"], person.get("specialty"))
    _pair_block(doc, L["degree"], person.get("degree"),
                L["title_sci"], [person.get("title")])
    _pair_block(doc, L["languages"], person.get("languages"),
                L["military"], [person.get("military")])

    _single(doc, L["awards"], person.get("awards"))

    # --- депутатлик
    p = _para(doc, before=6)
    _text(p, L["deputy"], bold=True)
    deputy = person.get("deputy") or []
    if deputy:
        _history(doc, deputy, before=0)
    else:
        p = _para(doc); _text(p, L["none"])

    # --- меҳнат фаолияти
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, before=12, after=4, keep_next=True)
    _text(p, L["work"], BIG, True)
    _history(doc, person.get("work", []))

    # --- 2-sahifa
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.page_break_before = True
    _text(p, L["rel1"].format(fio=person["fio"]), BIG, True)
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    _text(p, L["rel2"], BIG, True)
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.line_spacing = Pt(5.5)
    r = p.add_run(""); _set_font(r, 5)

    rels = person.get("relatives", [])
    brk = re.compile(r"^(Пенсияда|Pensiyada|Retired|На пенсии)\s*\(")
    for rel in rels:
        rel = rel  # joyida o'zgartiriladi
        if "\n" not in rel["work"]:
            rel["work"] = brk.sub(lambda m: m.group(1) + "\n(", rel["work"])
        if "\n" not in rel["birth"] and "," in rel["birth"]:
            y, rest = rel["birth"].split(",", 1)
            rel["birth"] = y.strip() + ",\n" + rest.strip()
    t = doc.add_table(rows=1 + len(rels), cols=5)
    t.autofit = False
    tblPr = t._tbl.tblPr
    # aniq kenglik, chap surilish va katak ichki oraliqlari (namunadagidek)
    for tag in ("w:tblW", "w:tblInd", "w:tblLayout", "w:tblCellMar"):
        for e in tblPr.findall(qn(tag)):
            tblPr.remove(e)
    w = OxmlElement("w:tblW"); w.set(qn("w:w"), str(sum(REL_COLS))); w.set(qn("w:type"), "dxa")
    ind = OxmlElement("w:tblInd"); ind.set(qn("w:w"), "108"); ind.set(qn("w:type"), "dxa")
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed")
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", 0), ("left", 108), ("bottom", 0), ("right", 108)):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    for e in (w, ind, lay, mar):
        tblPr.append(e)
    grid = t._tbl.tblGrid
    for gc, wd in zip(grid.findall(qn("w:gridCol")), REL_COLS):
        gc.set(qn("w:w"), str(wd))

    def set_widths(row):
        for c, wd in zip(row.cells, REL_COLS):
            c.width = Twips(wd)

    hdr = t.rows[0]
    set_widths(hdr)
    for c, txt in zip(hdr.cells, L["headers"]):
        _cell_text(c, txt, bold=True, wide=(c is hdr.cells[0]))
    # sarlavha qatori sahifa bo'linganda takrorlansin
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); trPr.append(th)

    for row, rel in zip(t.rows[1:], rels):
        set_widths(row)
        cs = row.cells
        _cell_text(cs[0], rel["relation"], bold=True, wide=True)
        _cell_text(cs[1], rel["fio"])
        _cell_text(cs[2], rel["birth"])
        if rel.get("deceased"):
            merged = cs[3].merge(cs[4])
            # merge qilingan katakdagi ortiqcha bo'sh paragrafni tozalaymiz
            for extra in merged.paragraphs[1:]:
                extra._element.getparent().remove(extra._element)
            _cell_text(merged, rel["work"])
        else:
            _cell_text(cs[3], rel["work"])
            _cell_text(cs[4], rel["residence"])
        # qator sahifa orasida bo'linib ketmasin
        trPr = row._tr.get_or_add_trPr()
        cs_ = OxmlElement("w:cantSplit"); trPr.append(cs_)

    # jadvaldan keyingi bo'sh paragraf (Word talabi)
    p = _para(doc); p.paragraph_format.line_spacing = Pt(3.5)
    r = p.add_run(""); _set_font(r, 3)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


# -------------------------------------------------------------- fayl nomi
_TRANSLIT_NAME = str.maketrans({"Ў": "У", "ў": "у", "Қ": "К", "қ": "к",
                                "Ғ": "Г", "ғ": "г", "Ҳ": "Х", "ҳ": "х"})


def file_name(fio: str, ext: str = ".docx") -> str:
    """Namunadagi qoida: ў,қ,ғ,ҳ o'rniga у,к,г,х; to'liq F.I.Sh. kirillda."""
    return " ".join(fio.split()).translate(_TRANSLIT_NAME) + ext

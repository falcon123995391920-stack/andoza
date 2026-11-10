"""Hujjat tili: o'zbek kirill (standart), o'zbek lotin, rus, ingliz.

Ichki ma'lumot (core) doim kirill shaklida; chiqarishdan oldin `localize()` uni tanlangan tilga o'tkazadi.
Foydalanuvchi kiritgan matn: lotin <-> kirill avtomatik o'giriladi (o'zbekcha), rus/ingliz hujjatda o'zgarmaydi.
"""
from __future__ import annotations

import copy
import re

LANGS = ("cy", "uz", "ru", "en")

# ------------------------------------------------------------ yozuv o'girish
_CYR_L = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y",
          "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
          "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ʼ", "ы": "i", "ь": "",
          "э": "e", "ю": "yu", "я": "ya", "ў": "oʻ", "қ": "q", "ғ": "gʻ", "ҳ": "h", "е": "e"}
_CYR_VOWELS = set("аеёиоуўэюяы")
_CYR_WORD = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]+")
_LAT_WORD = re.compile(r"[A-Za-z]+(?:['’ʻʼ‘`][A-Za-z]+)*['’ʻʼ‘`]?")
_KEEP_LATIN = {"phd", "dsc", "mba", "it", "id", "ceo", "sms", "wifi", "pc", "usa", "ai", "ngo", "ok"}


def _cyr_word_to_lat(w: str) -> str:
    low = w.lower(); allcap = len(w) > 1 and w.isupper()
    out = []
    for i, ch in enumerate(low):
        if ch == "е":
            prev = low[i - 1] if i else ""
            s = "ye" if (i == 0 or prev in _CYR_VOWELS or prev in "ъь") else "e"
        else:
            s = _CYR_L.get(ch, ch)
        if w[i].isupper():
            s = s.upper() if allcap else s[:1].upper() + s[1:]
        out.append(s)
    return "".join(out)


def cyr_to_lat(text: str) -> str:
    return _CYR_WORD.sub(lambda m: _cyr_word_to_lat(m.group(0)), text or "")


def _lat_word_to_cyr(w: str) -> str:
    if w.lower() in _KEEP_LATIN:
        return w
    s = w; i = 0; out = []
    apos = "'’ʻʼ‘`"
    start = lambda k: k == 0 or not s[k - 1].isalpha() and s[k - 1] not in apos
    allcap = len(w) > 1 and w.replace("'", "").isupper()
    def cap(x, up):
        if not up:
            return x
        return x.upper() if allcap else x[:1].upper() + x[1:]
    while i < len(s):
        c = s[i]; lo = c.lower(); up = c.isupper(); n = s[i + 1].lower() if i + 1 < len(s) else ""
        n2 = s[i + 2] if i + 2 < len(s) else ""
        if lo in "og" and n and n in apos:
            out.append(cap("ў" if lo == "o" else "ғ", up)); i += 2; continue
        if lo == "s" and n == "h": out.append(cap("ш", up)); i += 2; continue
        if lo == "c" and n == "h": out.append(cap("ч", up)); i += 2; continue
        if lo == "y" and n == "o" and n2 not in apos: out.append(cap("ё", up)); i += 2; continue
        if lo == "y" and n == "u": out.append(cap("ю", up)); i += 2; continue
        if lo == "y" and n == "a": out.append(cap("я", up)); i += 2; continue
        if lo == "y" and n == "e": out.append(cap("е", up)); i += 2; continue
        if lo == "e": out.append(cap("э" if start(i) else "е", up)); i += 1; continue
        if c in apos: out.append("ъ"); i += 1; continue
        m = {"a": "а", "b": "б", "d": "д", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л",
             "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
             "x": "х", "y": "й", "z": "з", "c": "ц", "w": "в"}.get(lo)
        out.append(cap(m, up) if m else c); i += 1
    return "".join(out)


def lat_to_cyr(text: str) -> str:
    return _LAT_WORD.sub(lambda m: _lat_word_to_cyr(m.group(0)), text or "")


def to_cyrillic(obj):
    """Ma'lumotdagi hamma matnni kirillga (tekshiruv uchun)."""
    return _map_strings(obj, lat_to_cyr)


def _map_strings(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_map_strings(x, fn) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_map_strings(x, fn) for x in obj)
    if isinstance(obj, dict):
        return {k: _map_strings(v, fn) for k, v in obj.items()}
    return obj


# ------------------------------------------------------------ hujjat yorliqlari
_CY = {
    "title": "МАЪЛУМОТНОМА",
    "birth_date": "Туғилган йили:", "birth_place": "Туғилган жойи:", "nationality": "Миллати:",
    "party": "Партиявийлиги:", "education": "Маълумоти:", "graduated": "Тамомлаган:",
    "specialty": "Маълумоти бўйича мутахассислиги:", "degree": "Илмий даражаси:", "title_sci": "Илмий унвони:",
    "languages": "Қайси чет тилларини билади:", "military": "Ҳарбий (махсус) унвони:",
    "awards": "Давлат мукофотлари билан тақдирланганми (қанақа):",
    "deputy": "Халқ депутатлари республика, вилоят, шаҳар ва туман Кенгаши депутатими ёки бошқа сайланадиган "
              "органларнинг аъзосими (тўлиқ кўрсатилиши лозим):",
    "none": "йўқ", "work": "МЕҲНАТ ФАОЛИЯТИ",
    "rel1": "{fio}нинг яқин қариндошлари ҳақида", "rel2": "МАЪЛУМОТ",
    "headers": ["Қарин-\nдошлиги", "Фамилияси, исми\nва отасининг исми", "Туғилган йили\nва жойи",
                "Иш жойи ва лавозими", "Турар жойи"],
}
_RU = {
    "title": "СПРАВКА", "birth_date": "Год рождения:", "birth_place": "Место рождения:",
    "nationality": "Национальность:", "party": "Партийность:", "education": "Образование:", "graduated": "Окончил(а):",
    "specialty": "Специальность по образованию:", "degree": "Учёная степень:", "title_sci": "Учёное звание:",
    "languages": "Какими иностранными языками владеет:", "military": "Воинское (специальное) звание:",
    "awards": "Награждён(а) ли государственными наградами (какими):",
    "deputy": "Является ли депутатом Кенгаша народных депутатов (республиканского, областного, городского, "
              "районного) или членом других выборных органов (указать полностью):",
    "none": "нет", "work": "ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ",
    "rel1": "{fio}", "rel2": "СВЕДЕНИЯ О БЛИЗКИХ РОДСТВЕННИКАХ",
    "headers": ["Степень\nродства", "Фамилия, имя\nи отчество", "Год и место\nрождения",
                "Место работы и должность", "Место жительства"],
}
_EN = {
    "title": "BIOGRAPHICAL INFORMATION", "birth_date": "Date of birth:", "birth_place": "Place of birth:",
    "nationality": "Nationality:", "party": "Party affiliation:", "education": "Education:", "graduated": "Graduated:",
    "specialty": "Specialty by education:", "degree": "Academic degree:", "title_sci": "Academic title:",
    "languages": "Foreign languages:", "military": "Military (special) rank:",
    "awards": "State awards (which):",
    "deputy": "Deputy of a republican, regional, city or district council of people's deputies, or member of "
              "other elected bodies (state in full):",
    "none": "none", "work": "WORK HISTORY",
    "rel1": "{fio}", "rel2": "INFORMATION ABOUT CLOSE RELATIVES",
    "headers": ["Relation", "Full name", "Year and place\nof birth", "Workplace and position", "Residence"],
}
_UZ = {k: (cyr_to_lat(v) if isinstance(v, str) else [cyr_to_lat(x) for x in v]) for k, v in _CY.items()}
_UZ["title"] = "MAʼLUMOTNOMA"
_UZ["rel1"] = "{fio}ning yaqin qarindoshlari haqida"
_UZ["rel2"] = "MAʼLUMOT"
LABELS = {"cy": _CY, "uz": _UZ, "ru": _RU, "en": _EN}

_REL = {  # kanonik kirill -> (ru, en)
    "Отаси": ("Отец", "Father"), "Онаси": ("Мать", "Mother"), "Акаси": ("Старший брат", "Elder brother"),
    "Опаси": ("Старшая сестра", "Elder sister"), "Укаси": ("Младший брат", "Younger brother"),
    "Синглиси": ("Младшая сестра", "Younger sister"), "Турмуш ўртоғи": ("Супруг(а)", "Spouse"),
    "Ўғли": ("Сын", "Son"), "Қизи": ("Дочь", "Daughter"), "Қайнотаси": ("Тесть / свёкор", "Father-in-law"),
    "Қайнонаси": ("Тёща / свекровь", "Mother-in-law"),
}
_LANGNAME = {"рус": ("русский", "Russian"), "инглиз": ("английский", "English"), "немис": ("немецкий", "German"),
             "француз": ("французский", "French"), "испан": ("испанский", "Spanish"),
             "итальян": ("итальянский", "Italian"), "турк": ("турецкий", "Turkish"), "араб": ("арабский", "Arabic"),
             "хитой": ("китайский", "Chinese"), "япон": ("японский", "Japanese"), "корейс": ("корейский", "Korean")}
_VALUES = {  # ma'lum qiymatlar
    "олий": ("высшее", "higher"), "ўрта махсус": ("среднее специальное", "secondary specialized"),
    "ўрта": ("среднее", "secondary"), "тугалланмаган олий": ("неполное высшее", "incomplete higher"),
    "ўзбек": ("узбек", "Uzbek"), "қорақалпоқ": ("каракалпак", "Karakalpak"), "тожик": ("таджик", "Tajik"),
    "қозоқ": ("казах", "Kazakh"), "рус": ("русский", "Russian"), "татар": ("татарин", "Tatar"),
    "қирғиз": ("киргиз", "Kyrgyz"), "тюрк": ("турок", "Turkish"), "уйғур": ("уйгур", "Uyghur"),
    "ўзбекистон либерал-демократик партияси аъзоси": ("член Либерально-демократической партии Узбекистана", "member of the Liberal Democratic Party of Uzbekistan"),
    "ўзбекистон миллий тикланиш демократик партияси аъзоси": ("член Демократической партии «Миллий тикланиш» Узбекистана", "member of the “Milliy Tiklanish” Democratic Party of Uzbekistan"),
    "ўзбекистон халқ демократик партияси аъзоси": ("член Народно-демократической партии Узбекистана", "member of the People's Democratic Party of Uzbekistan"),
    "«адолат» социал-демократик партияси аъзоси": ("член Социал-демократической партии «Адолат»", "member of the “Adolat” Social Democratic Party"),
    "«экологик партия» аъзоси": ("член Экологической партии", "member of the Ecological Party"),
}
_MONTH_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
_MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
_MONTH_KEYS = ["январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]
_NONE_SET = {"йўқ", "yo'q", "yo‘q", "yoq", "yo`q", "нет", "none", "no", "-", "—"}


def is_none(s: str) -> bool:
    return (s or "").strip().lower().rstrip(".") in _NONE_SET


def _ix(lang):
    return 0 if lang == "ru" else 1


def _tr_period(s: str, lang: str) -> str:
    """Davr / yil qo'shimchalari: yy., й., ҳ.в."""
    ru = lang == "ru"
    s = re.sub(r"(\d{4})-(\d{4}) йй\.", (r"\1-\2 гг." if ru else r"\1-\2"), s)
    s = re.sub(r"(\d{4}) й\.(\s+)-(\s+)ҳ\.в\.", (r"\1 г.\2-\3н.в." if ru else r"\1\2-\3present"), s)
    s = re.sub(r"^(\d{4}) й\.$", (r"\1 г." if ru else r"\1"), s)
    return s


def _tr_year_prefix(s: str, lang: str) -> str:
    ru = lang == "ru"
    return re.sub(r"^(\d{4}) й\.\s*", (r"\1 г. " if ru else r"\1: "), s)


def _tr_job_since(s: str, lang: str) -> str:
    m = re.match(r"^\s*(\d{4}) йил (\d{1,2}) ([а-яўқғҳ]+?)дан:?$", s or "", re.I)
    if not m:
        return s
    for i, key in enumerate(_MONTH_KEYS):
        if m.group(3).lower().startswith(key):
            d, y = int(m.group(2)), m.group(1)
            return f"С {d} {_MONTH_RU[i]} {y} г.:" if lang == "ru" else f"Since {_MONTH_EN[i]} {d}, {y}:"
    return s


def _tr_languages(s: str, lang: str) -> str:
    t = re.sub(r"\s*тил(?:и|лари)\s*\.?$", "", (s or "").strip(), flags=re.I)
    parts = [x.strip() for x in re.split(r"[,;]", t) if x.strip()]
    out = [(_LANGNAME[p.lower()][_ix(lang)] if p.lower() in _LANGNAME else p) for p in parts]
    return ", ".join(out) if out else s


def _tr_value(s: str, lang: str) -> str:
    if is_none(s):
        return LABELS[lang]["none"]
    v = _VALUES.get((s or "").strip().lower())
    return v[_ix(lang)] if v else s


def _tr_rel_work(s: str, lang: str) -> str:
    ru = lang == "ru"
    m = re.match(r"^(?:(\d{4}) йил )?вафот этган\s*(?:\((.*)\))?$", s or "", re.S)
    if m:
        year, job = m.group(1), m.group(2)
        head = (f"Умер(ла) в {year} г." if year else "Умер(ла)") if ru else (f"Died in {year}" if year else "Deceased")
        return f"{head}\n({job})" if job else head
    m = re.match(r"^Пенсияда\s*(?:\((.*)\))?$", s or "", re.S)
    if m:
        head = "На пенсии" if ru else "Retired"
        return f"{head}\n({m.group(1)})" if m.group(1) else head
    return s


def _tr_rel_birth(s: str, lang: str) -> str:
    ru = lang == "ru"
    return re.sub(r"^(\d{4}) йил\s*,?\s*", (r"\1 г., " if ru else r"\1, "), s or "")


def _break_status(s: str) -> str:
    """Kirill/lotin: 'Пенсияда (…)' va 'N йил вафот этган (…)' ni qavs oldidan yangi qatorga bo'lamiz."""
    if "\n" in s:
        return s
    return re.sub(r"^(Пенсияда|(?:\d{4} йил )?вафот этган)\s*\(", lambda m: m.group(1) + "\n(", s)


def localize(std: dict, lang: str) -> dict:
    """Standartlangan (kirill) ma'lumotni hujjat tiliga o'tkazadi."""
    lang = lang if lang in LANGS else "cy"
    q = copy.deepcopy(std)
    for r in q.get("relatives", []):
        r["work"] = _break_status(r.get("work", ""))
        if "\n" not in r.get("birth", "") and "," in r.get("birth", ""):
            pass  # builder bo'ladi
    if lang in ("cy", "uz"):
        conv = lat_to_cyr if lang == "cy" else cyr_to_lat
        flags = {r.get("fio"): r.get("deceased") for r in q.get("relatives", [])}
        for r in q.get("relatives", []):
            dec = r.get("deceased")
            for k in ("relation", "fio", "birth", "work", "residence"):
                r[k] = conv(r.get(k, ""))
            if dec:
                r["deceased"] = True
        for k in ("fio", "job_since", "position", "birth_date", "birth_place", "nationality", "party", "education",
                  "specialty", "degree", "title", "languages", "military", "awards"):
            if k in q:
                q[k] = conv(q[k])
        q["graduated"] = [conv(g) for g in q.get("graduated", [])]
        q["deputy"] = [[conv(a), conv(b)] for a, b in q.get("deputy", [])]
        q["work"] = [[conv(a), conv(b)] for a, b in q.get("work", [])]
        if lang == "uz":                      # "ҳ.в." -> "h.v.", yil qo'shimchalari lotinda
            for lst in (q["deputy"], q["work"]):
                for row in lst:
                    row[0] = row[0].replace("h.v.", "h.v.")
        return q
    # --- rus / ingliz
    ix = _ix(lang)
    for k in ("party", "military", "degree", "title", "awards"):
        q[k] = _tr_value(q.get(k, ""), lang)
    for k in ("nationality", "education"):
        q[k] = _tr_value(q.get(k, ""), lang)
    q["job_since"] = _tr_job_since(q.get("job_since", ""), lang)
    q["languages"] = _tr_languages(q.get("languages", ""), lang)
    q["graduated"] = [_tr_year_prefix(g, lang) for g in q.get("graduated", [])]
    if not is_none(q.get("awards", "")):
        q["awards"] = "; ".join(_tr_year_prefix(x, lang) for x in re.split(r"\s*;\s*", q["awards"]))
    q["deputy"] = [[_tr_period(a, lang), b] for a, b in q.get("deputy", [])]
    q["work"] = [[_tr_period(a, lang), b] for a, b in q.get("work", [])]
    for r in q.get("relatives", []):
        r["relation"] = _REL.get(r.get("relation", ""), (r.get("relation", ""),) * 2)[ix]
        r["birth"] = _tr_rel_birth(r.get("birth", ""), lang)
        r["work"] = _tr_rel_work(r.get("work", "").replace("\n", " "), lang)
    if lang == "en":
        q = _map_strings(q, cyr_to_lat)
    return q


# ------------------------------------------------------------ ogohlantirishlar tili
_WHERE = {
    "F.I.Sh.": ("Ф.И.О.", "Full name"), "Жорий лавозими": ("Текущая должность", "Current position"),
    "Жорий лавозим": ("Текущая должность", "Current position"),
    "Туғилган йили": ("Дата рождения", "Date of birth"), "Туғилган жойи": ("Место рождения", "Place of birth"),
    "Миллати": ("Национальность", "Nationality"), "Маълумоти": ("Образование", "Education"),
    "Мутахассислиги": ("Специальность", "Specialty"), "Тамомлаган": ("Окончил(а)", "Graduated"),
    "Мукофотлар": ("Награды", "Awards"), "Чет тиллари": ("Иностранные языки", "Foreign languages"),
    "Меҳнат фаолияти": ("Трудовая деятельность", "Work history"), "Яқин қариндошлар": ("Близкие родственники", "Close relatives"),
}
_MSG = [  # (regex, ru, en)
    (r"^Ф\.И\.Ш\. тўлиқ \(фамилия, исм, шариф\) бўлиши керак$", "Ф.И.О. должно быть полным (фамилия, имя, отчество)", "Full name is required (surname, name, patronymic)"),
    (r"^тўлдирилмаган$", "не заполнено", "not filled in"),
    (r"^сана КК\.ОО\.ЙЙЙЙ шаклида бўлиши керак$", "дата должна быть в формате ДД.ММ.ГГГГ", "date must be DD.MM.YYYY"),
    (r"^«Идоравий мукофотлар».*$", "«Ведомственные награды» добавлены в строку государственных наград — в стандарте указываются только государственные, проверьте", "“Departmental awards” were merged into state awards — the standard lists state awards only, please check"),
    (r"^даража олиб ташланди.*$", "уровень владения удалён (указываются только языки) — проверьте", "proficiency level removed (only language names are listed) — please check"),
    (r"^фақат тил номлари ёзилади.*$", "указываются только названия языков: «русский, английский» (без уровня)", "write language names only: “Russian, English” (no level)"),
    (r"^вилоят ва туман \(шаҳар\) тўлиқ кўрсатилиши керак$", "должны быть указаны область и район (город)", "region and district (city) must be given in full"),
    (r"^тамомлаган ўқув юрти кўрсатилмаган$", "учебное заведение не указано", "institution not specified"),
    (r"^ёзувлар топилмади$", "записи не найдены", "no entries found"),
    (r"^қисқартма бор — тўлиқ ёзилиши керак$", "есть сокращение — пишите полностью", "abbreviation found — write in full"),
    (r"^«(.+)» — «ҳ\.в\.» фақат охирги ёзувда бўлади$", "«\\1» — «н.в.» допускается только в последней записи", "“\\1” — “present” is allowed in the last entry only"),
    (r"^давр аниқланмади: «(.*)»$", "период не распознан: «\\1»", "period not recognized: “\\1”"),
    (r"^(\d{4}) ва (\d{4}) йиллар орасида бўшлиқ бор$", "между \\1 и \\2 годами есть пробел", "gap between \\1 and \\2"),
    (r"^(.+): давр олдингиси билан кесишади$", "\\1: период пересекается с предыдущим", "\\1: period overlaps the previous one"),
    (r"^жадвал топилмади$", "таблица не найдена", "no relatives found"),
    (r"^матндан автоматик ажратилди — маълумотларни текширинг$", "определено из текста автоматически — проверьте данные", "extracted from text automatically — please check"),
    (r"^қариндошлиги аниқланмади$", "степень родства не определена", "relation not recognized"),
    (r"^қариндошлик «Ўғли».*$", "степень родства пишется «Сын/Дочь/Супруг(а)», а не «мой сын» и т.п.", "write the relation as Son/Daughter/Spouse, not “my son”"),
    (r"^Ф\.И\.Ш\. тўлиқ эмас$", "Ф.И.О. указано не полностью", "full name is incomplete"),
    (r"^Ф\.И\.Ш\. да бош ҳарф билан қисқартма бор$", "в Ф.И.О. есть сокращение инициалами", "initials used in the name"),
    (r"^туғилган йили «1976 йил, …» шаклида бўлиши керак$", "год рождения в формате «1976 г., …»", "year of birth must be like “1976, …”"),
    (r"^туғилган жойи: вилоят ва туман \(шаҳар\) тўлиқ кўрсатилиши керак$", "место рождения: укажите область и район (город) полностью", "place of birth: give region and district (city) in full"),
    (r"^«2000 йил вафот этган \(аввалги лавозими\)» шаклида ёзилсин$", "формат: «Умер в 2000 г. (прежняя должность)»", "format: “Died in 2000 (former position)”"),
    (r"^вафот этган бўлса, аввалги лавозими қавсда кўрсатилсин$", "для умершего прежняя должность указывается в скобках", "for a deceased person give the former position in brackets"),
    (r"^пенсияда бўлса, аввалги лавозими қавсда кўрсатилсин$", "для пенсионера прежняя должность указывается в скобках", "for a retiree give the former position in brackets"),
    (r"^«илгари», «бўлган» сўзлари ёзилмайди$", "слова «ранее», «бывший» не пишутся", "do not write “formerly” / “was”"),
    (r"^иш жойи ва лавозими кўрсатилмаган$", "место работы и должность не указаны", "workplace and position not specified"),
    (r"^иш жойида қисқартма бор — тўлиқ ёзилсин$", "в месте работы есть сокращение — пишите полностью", "abbreviation in workplace — write in full"),
    (r"^турар жойи кўрсатилмаган$", "место жительства не указано", "residence not specified"),
    (r"^турар жойида вилоят, шаҳар, туман номлари тўлиқ кўрсатилсин$", "место жительства: области, города, районы пишите полностью", "residence: write region, city and district names in full"),
]
_MSG_C = [(re.compile(a, re.S), b, c) for a, b, c in _MSG]


def _tr_who(where: str, lang: str) -> str:
    m = re.match(r"^(.+?) \((.*)\)$", where)
    if m and m.group(1) in _REL:
        return f"{_REL[m.group(1)][_ix(lang)]} ({m.group(2)})"
    return where


def warn_text(where: str, msg: str, lang: str):
    """core.check() matnlarini interfeys tiliga o'tkazadi (asl: kirill)."""
    if lang == "cy":
        return where, msg
    if lang == "uz":
        return cyr_to_lat(where), cyr_to_lat(msg)
    ix = _ix(lang)
    w = None
    for pre in ("Меҳнат фаолияти", "Депутатлик"):
        if where.startswith(pre + " "):
            base = _WHERE.get(pre, ("Депутатство", "Deputy"))[ix] if pre == "Меҳнат фаолияти" else ("Депутатство", "Deputy")[ix]
            w = f"{base} {_tr_period(where[len(pre) + 1:], lang)}"
    if w is None:
        w = _WHERE.get(where, (None, None))[ix] or _tr_who(where, lang)
    for rx, ru, en in _MSG_C:
        m = rx.match(msg)
        if m:
            return w, m.expand(ru if lang == "ru" else en)
    return w, msg


REPORT = {
    "cy": {"ok": "ОК", "err": "ХАТО", "warns": "та огоҳлантириш"},
    "uz": {"ok": "OK", "err": "XATO", "warns": "ta ogohlantirish"},
    "ru": {"ok": "ОК", "err": "ОШИБКА", "warns": "предупреждений"},
    "en": {"ok": "OK", "err": "ERROR", "warns": "warnings"},
}

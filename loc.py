"""Hujjat tili: Word hujjatdagi sarlavha/yorliqlar va avtomatik yoziladigan iboralar tanlangan tilga moslanadi.
Ichki (kanonik) ma'lumot kirillda saqlanadi; bu modul uni faqat chiqarish paytida tarjima qiladi.
Tillar: cy = o'zbek (kirill, standart), uz = o'zbek (lotin), ru = rus, en = ingliz."""
from __future__ import annotations

import re

LANGS = ("cy", "uz", "ru", "en")


def norm_lang(l) -> str:
    return l if l in LANGS else "cy"


W_LANG = {"cy": "uz-Cyrl-UZ", "uz": "uz-Latn-UZ", "ru": "ru-RU", "en": "en-US"}

# ------------------------------------------------------------------ hujjat yorliqlari
DOC = {
    "cy": dict(
        title="МАЪЛУМОТНОМА", birth_date="Туғилган йили:", birth_place="Туғилган жойи:", nationality="Миллати:",
        party="Партиявийлиги:", education="Маълумоти:", graduated="Тамомлаган:",
        specialty="Маълумоти бўйича мутахассислиги:", degree="Илмий даражаси:", ttitle="Илмий унвони:",
        languages="Қайси чет тилларини билади:", military="Ҳарбий (махсус) унвони:",
        awards="Давлат мукофотлари билан тақдирланганми (қанақа):",
        deputy="Халқ депутатлари республика, вилоят, шаҳар ва туман Кенгаши депутатими ёки бошқа сайланадиган органларнинг аъзосими (тўлиқ кўрсатилиши лозим):",
        none="йўқ", work="МЕҲНАТ ФАОЛИЯТИ", rel_title="{fio}нинг яқин қариндошлари ҳақида", info="МАЪЛУМОТ",
        headers=["Қарин-\nдошлиги", "Фамилияси, исми\nва отасининг исми", "Туғилган йили\nва жойи", "Иш жойи ва лавозими", "Турар жойи"]),
    "uz": dict(
        title="MA'LUMOTNOMA", birth_date="Tug'ilgan yili:", birth_place="Tug'ilgan joyi:", nationality="Millati:",
        party="Partiyaviyligi:", education="Ma'lumoti:", graduated="Tamomlagan:",
        specialty="Ma'lumoti bo'yicha mutaxassisligi:", degree="Ilmiy darajasi:", ttitle="Ilmiy unvoni:",
        languages="Qaysi chet tillarini biladi:", military="Harbiy (maxsus) unvoni:",
        awards="Davlat mukofotlari bilan taqdirlanganmi (qanaqa):",
        deputy="Xalq deputatlari respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa saylanadigan organlarning a'zosimi (to'liq ko'rsatilishi lozim):",
        none="yo'q", work="MEHNAT FAOLIYATI", rel_title="{fio}ning yaqin qarindoshlari haqida", info="MA'LUMOT",
        headers=["Qarin-\ndoshligi", "Familiyasi, ismi\nva otasining ismi", "Tug'ilgan yili\nva joyi", "Ish joyi va lavozimi", "Turar joyi"]),
    "ru": dict(
        title="СПРАВКА", birth_date="Год рождения:", birth_place="Место рождения:", nationality="Национальность:",
        party="Партийность:", education="Образование:", graduated="Окончил(а):",
        specialty="Специальность по образованию:", degree="Учёная степень:", ttitle="Учёное звание:",
        languages="Какими иностранными языками владеет:", military="Воинское (специальное) звание:",
        awards="Награждён(а) ли государственными наградами (какими):",
        deputy="Является ли депутатом Народных депутатов республиканского, областного, городского или районного Кенгаша либо членом иных выборных органов (указать полностью):",
        none="нет", work="ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ", rel_title="Ближайшие родственники: {fio}", info="СВЕДЕНИЯ",
        headers=["Степень\nродства", "Фамилия, имя\nи отчество", "Год и место\nрождения", "Место работы и должность", "Место жительства"]),
    "en": dict(
        title="BIOGRAPHICAL SUMMARY", birth_date="Date of birth:", birth_place="Place of birth:", nationality="Nationality:",
        party="Party affiliation:", education="Education:", graduated="Graduated from:",
        specialty="Specialty:", degree="Academic degree:", ttitle="Academic title:",
        languages="Foreign languages:", military="Military (special) rank:",
        awards="State awards (which):",
        deputy="Is a deputy of a republican, regional, city or district Kengash, or a member of other elected bodies (specify in full):",
        none="none", work="WORK HISTORY", rel_title="Close relatives of {fio}", info="INFORMATION",
        headers=["Relation", "Full name", "Year and place\nof birth", "Workplace and position", "Residence"]),
}

NONE_CY = "йўқ"
OY_CY = ["январдан", "февралдан", "мартдан", "апрелдан", "майдан", "июндан", "июлдан", "августдан", "сентябрдан", "октябрдан", "ноябрдан", "декабрдан"]
OY = {
    "uz": ["yanvardan", "fevraldan", "martdan", "apreldan", "maydan", "iyundan", "iyuldan", "avgustdan", "sentabrdan", "oktabrdan", "noyabrdan", "dekabrdan"],
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
REL = {  # kanonik -> (uz, ru, en)
    "Отаси": ("Otasi", "Отец", "Father"), "Онаси": ("Onasi", "Мать", "Mother"),
    "Акаси": ("Akasi", "Старший брат", "Elder brother"), "Опаси": ("Opasi", "Старшая сестра", "Elder sister"),
    "Укаси": ("Ukasi", "Младший брат", "Younger brother"), "Синглиси": ("Singlisi", "Младшая сестра", "Younger sister"),
    "Турмуш ўртоғи": ("Turmush o'rtog'i", "Супруг(а)", "Spouse"), "Ўғли": ("O'g'li", "Сын", "Son"), "Қизи": ("Qizi", "Дочь", "Daughter"),
    "Қайнотаси": ("Qaynotasi", "Тесть / свёкор", "Father-in-law"), "Қайнонаси": ("Qaynonasi", "Тёща / свекровь", "Mother-in-law"),
}
LANGNAME = {  # kanonik -> (uz, ru, en)
    "рус": ("rus", "русский", "Russian"), "инглиз": ("ingliz", "английский", "English"), "немис": ("nemis", "немецкий", "German"),
    "француз": ("fransuz", "французский", "French"), "испан": ("ispan", "испанский", "Spanish"), "итальян": ("italyan", "итальянский", "Italian"),
    "турк": ("turk", "турецкий", "Turkish"), "араб": ("arab", "арабский", "Arabic"), "хитой": ("xitoy", "китайский", "Chinese"),
    "япон": ("yapon", "японский", "Japanese"), "корейс": ("koreys", "корейский", "Korean"),
}
_IDX = {"uz": 0, "ru": 1, "en": 2}


# ------------------------------------------------------------------ iboralar
def fmt_year(y: str, lang: str) -> str:
    """'1950' -> 'йил' qo'shimchali shakl (ro'yxat uchun)"""
    return {"cy": f"{y} йил", "uz": f"{y}-yil", "ru": f"{y} г.", "en": y}[lang]


def fmt_period(s: str, lang: str) -> str:
    if lang == "cy" or not s:
        return s
    m = re.fullmatch(r"(\d{4})-(\d{4}) йй\.", s)
    if m:
        a, b = m.groups()
        return {"uz": f"{a}-{b} yy.", "ru": f"{a}-{b} гг.", "en": f"{a}-{b}"}[lang]
    m = re.fullmatch(r"(\d{4}) й\.\s*-\s*ҳ\.в\.", s)
    if m:
        a = m.group(1)
        return {"uz": f"{a} y.  -  h.v.", "ru": f"{a} г.  -  н.в.", "en": f"{a}  -  present"}[lang]
    m = re.fullmatch(r"(\d{4}) й\.", s)
    if m:
        a = m.group(1)
        return {"uz": f"{a} y.", "ru": f"{a} г.", "en": a}[lang]
    return s


def fmt_none(s: str, lang: str) -> str:
    if lang != "cy" and s and s.strip().lower().rstrip(".") == NONE_CY:
        return DOC[lang]["none"]
    return s


def fmt_job_since(s: str, lang: str) -> str:
    if lang == "cy" or not s:
        return s
    m = re.match(r"\s*(\d{4})\s*йил\s*(\d{1,2})\s+([а-яўқғҳ]+?)дан\s*:?", s, re.I)
    if not m:
        return s
    y, d, mon = m.group(1), int(m.group(2)), m.group(3).lower()
    k = next((i for i, n in enumerate(OY_CY) if n.startswith(mon)), None)
    if k is None:
        return s
    if lang == "uz":
        return f"{y}-yil {d}-{OY['uz'][k]}:"
    if lang == "ru":
        return f"С {d} {OY['ru'][k]} {y} года:"
    return f"Since {OY['en'][k]} {d}, {y}:"


def fmt_langs(s: str, lang: str) -> str:
    if lang == "cy" or not s:
        return s
    m = re.fullmatch(r"\s*(.+?)\s+тил(?:и|лари)\s*", s)
    if not m:
        return s
    names = [x.strip() for x in m.group(1).split(",") if x.strip()]
    i = _IDX[lang]
    out = [LANGNAME[n][i] if n in LANGNAME else n for n in names]
    if lang == "uz":
        return (out[0] + " tili") if len(out) == 1 else ", ".join(out) + " tillari"
    return ", ".join(out)


def fmt_year_item(s: str, lang: str) -> str:
    """'1995 й. Университет' -> tilga moslangan"""
    if lang == "cy":
        return s
    m = re.match(r"^(\d{4}) й\.\s*(.*)$", s or "")
    if not m:
        return s
    y, rest = m.groups()
    return {"uz": f"{y}-yil {rest}", "ru": f"{y} г. {rest}", "en": f"{y}: {rest}"}[lang].strip()


def fmt_rel(rel: dict, lang: str) -> dict:
    if lang == "cy":
        return rel
    r = dict(rel)
    i = _IDX[lang]
    if r.get("relation") in REL:
        r["relation"] = REL[r["relation"]][i]
    m = re.match(r"^(\d{4}) йил(?:,\s*(.*))?$", r.get("birth", ""), re.S)
    if m:
        y, rest = m.group(1), m.group(2)
        head = fmt_year(y, lang)
        r["birth"] = head + (f", {rest}" if rest else "")
    w = r.get("work", "")
    wn = re.sub(r"\s*\n\s*", " ", w)
    mm = re.match(r"^Пенсияда(?:\s*\((.*)\))?$", wn, re.S)
    md = re.match(r"^(?:(\d{4}) йил )?вафот этган(?:\s*\((.*)\))?$", wn, re.S)
    if mm:
        pre = {"uz": "Pensiyada", "ru": "На пенсии", "en": "Retired"}[lang]
        r["work"] = pre + (f" ({mm.group(1)})" if mm.group(1) else "")
    elif md:
        y, wk = md.group(1), md.group(2)
        if lang == "uz":
            pre = (f"{y}-yil " if y else "") + "vafot etgan"
        elif lang == "ru":
            pre = f"Умер(ла) в {y} г." if y else "Умер(ла)"
        else:
            pre = f"Died in {y}" if y else "Deceased"
        r["work"] = pre + (f" ({wk})" if wk else "")
    return r


def localize_person(p: dict, lang: str) -> dict:
    lang = norm_lang(lang)
    if lang == "cy":
        return p
    q = dict(p)
    q["job_since"] = fmt_job_since(p.get("job_since", ""), lang)
    for k in ("party", "military", "degree", "title"):
        q[k] = fmt_none(p.get(k, ""), lang)
    aw = p.get("awards", "")
    q["awards"] = fmt_none(aw, lang) if aw.strip().lower().rstrip(".") == NONE_CY else \
        "; ".join(fmt_year_item(x, lang) for x in re.split(r"\s*;\s*", aw) if x)
    q["languages"] = fmt_langs(p.get("languages", ""), lang)
    q["graduated"] = [fmt_year_item(g, lang) for g in p.get("graduated", [])]
    q["deputy"] = [[fmt_period(a, lang), b] for a, b in p.get("deputy", [])]
    q["work"] = [[fmt_period(a, lang), b] for a, b in p.get("work", [])]
    q["relatives"] = [fmt_rel(r, lang) for r in p.get("relatives", [])]
    return q


# ================================================================== ogohlantirishlar
_WH = {  # kanonik 'where' -> til
    "F.I.Sh.": ("Ф.И.Ш.", "F.I.Sh.", "Ф.И.О.", "Full name"),
    "Туғилган йили": ("Туғилган йили", "Tug'ilgan yili", "Дата рождения", "Date of birth"),
    "Туғилган жойи": ("Туғилган жойи", "Tug'ilgan joyi", "Место рождения", "Place of birth"),
    "Миллати": ("Миллати", "Millati", "Национальность", "Nationality"),
    "Маълумоти": ("Маълумоти", "Ma'lumoti", "Образование", "Education"),
    "Мутахассислиги": ("Мутахассислиги", "Mutaxassisligi", "Специальность", "Specialty"),
    "Жорий лавозими": ("Жорий лавозими", "Joriy lavozimi", "Текущая должность", "Current position"),
    "Жорий лавозим": ("Жорий лавозим", "Joriy lavozim", "Текущая должность", "Current position"),
    "Мукофотлар": ("Мукофотлар", "Mukofotlar", "Награды", "Awards"),
    "Чет тиллари": ("Чет тиллари", "Chet tillari", "Иностранные языки", "Foreign languages"),
    "Тамомлаган": ("Тамомлаган", "Tamomlagan", "Образование (окончил)", "Graduated"),
    "Меҳнат фаолияти": ("Меҳнат фаолияти", "Mehnat faoliyati", "Трудовая деятельность", "Work history"),
    "Яқин қариндошлар": ("Яқин қариндошлар", "Yaqin qarindoshlar", "Ближайшие родственники", "Close relatives"),
}
_LI = {"cy": 0, "uz": 1, "ru": 2, "en": 3}
_MSG = {  # kanonik xabar -> (uz, ru, en)
    "Ф.И.Ш. тўлиқ (фамилия, исм, шариф) бўлиши керак": ("F.I.Sh. to'liq (familiya, ism, sharif) bo'lishi kerak", "Ф.И.О. должно быть полным (фамилия, имя, отчество)", "The full name must include surname, first name and patronymic"),
    "тўлдирилмаган": ("to'ldirilmagan", "не заполнено", "not filled in"),
    "сана КК.ОО.ЙЙЙЙ шаклида бўлиши керак": ("sana KK.OO.YYYY shaklida bo'lishi kerak", "дата должна быть в формате ДД.ММ.ГГГГ", "the date must be in DD.MM.YYYY format"),
    "«Идоравий мукофотлар» «Давлат мукофотлари» қаторига қўшилди — стандартда фақат давлат мукофотлари кўрсатилади, текширинг": ("«Idoraviy mukofotlar» «Davlat mukofotlari» qatoriga qo'shildi — standartda faqat davlat mukofotlari ko'rsatiladi, tekshiring", "«Ведомственные награды» добавлены к «Государственным наградам» — по стандарту указываются только государственные, проверьте", "“Departmental awards” were merged into “State awards” — the standard lists state awards only; please check"),
    "даража олиб ташланди (фақат мукаммал билинадиган тиллар ёзилади) — текширинг": ("daraja olib tashlandi (faqat mukammal biladigan tillar yoziladi) — tekshiring", "уровень владения удалён (указываются только языки, которыми владеют свободно) — проверьте", "proficiency level was removed (only fluent languages are listed) — please check"),
    "фақат тил номлари ёзилади: «рус, инглиз тиллари» (даража ёзилмайди)": ("faqat til nomlari yoziladi: «rus, ingliz tillari» (daraja yozilmaydi)", "указываются только названия языков: «русский, английский» (без уровня)", "write language names only: “Russian, English” (no proficiency level)"),
    "вилоят ва туман (шаҳар) тўлиқ кўрсатилиши керак": ("viloyat va tuman (shahar) to'liq ko'rsatilishi kerak", "область и район (город) нужно указать полностью", "region and district (city) must be given in full"),
    "тамомлаган ўқув юрти кўрсатилмаган": ("tamomlagan o'quv yurti ko'rsatilmagan", "оконченное учебное заведение не указано", "no graduated institution given"),
    "ёзувлар топилмади": ("yozuvlar topilmadi", "записи не найдены", "no entries found"),
    "қисқартма бор — тўлиқ ёзилиши керак": ("qisqartma bor — to'liq yozilishi kerak", "есть сокращение — нужно писать полностью", "contains an abbreviation — write it in full"),
    "жадвал топилмади": ("jadval topilmadi", "таблица не найдена", "no relatives added"),
    "матндан автоматик ажратилди — маълумотларни текширинг": ("matndan avtomatik ajratildi — ma'lumotlarni tekshiring", "разобрано из текста автоматически — проверьте данные", "parsed automatically from text — please check the data"),
    "қариндошлиги аниқланмади": ("qarindoshligi aniqlanmadi", "степень родства не определена", "relation not recognized"),
    "қариндошлик «Ўғли», «Рафиқа»… эмас, «Ўғли/Қизи/Турмуш ўртоғи» шаклида ёзилади": ("qarindoshlik «o'g'lim», «rafiqam»… emas, «O'g'li/Qizi/Turmush o'rtog'i» shaklida yoziladi", "степень родства пишется как «Сын/Дочь/Супруг(а)», а не «мой сын», «жена»…", "write the relation as “Son/Daughter/Spouse”, not “my son”, “wife”…"),
    "Ф.И.Ш. тўлиқ эмас": ("F.I.Sh. to'liq emas", "Ф.И.О. указано не полностью", "the full name is incomplete"),
    "Ф.И.Ш. да бош ҳарф билан қисқартма бор": ("F.I.Sh.da bosh harf bilan qisqartma bor", "в Ф.И.О. есть сокращение инициалами", "the name contains abbreviated initials"),
    "туғилган йили «1976 йил, …» шаклида бўлиши керак": ("tug'ilgan yili «1976 yil, …» shaklida bo'lishi kerak", "год рождения должен быть в виде «1976 г., …»", "the birth year must be written as “1976, …”"),
    "туғилган жойи: вилоят ва туман (шаҳар) тўлиқ кўрсатилиши керак": ("tug'ilgan joyi: viloyat va tuman (shahar) to'liq ko'rsatilishi kerak", "место рождения: область и район (город) нужно указать полностью", "place of birth: region and district (city) must be given in full"),
    "«2000 йил вафот этган (аввалги лавозими)» шаклида ёзилсин": ("«2000-yil vafot etgan (avvalgi lavozimi)» shaklida yozilsin", "пишите в виде «Умер в 2000 г. (прежняя должность)»", "write as “Died in 2000 (former position)”"),
    "вафот этган бўлса, аввалги лавозими қавсда кўрсатилсин": ("vafot etgan bo'lsa, avvalgi lavozimi qavsda ko'rsatilsin", "если умер(ла), прежняя должность указывается в скобках", "if deceased, give the former position in brackets"),
    "пенсияда бўлса, аввалги лавозими қавсда кўрсатилсин": ("pensiyada bo'lsa, avvalgi lavozimi qavsda ko'rsatilsin", "если на пенсии, прежняя должность указывается в скобках", "if retired, give the former position in brackets"),
    "«илгари», «бўлган» сўзлари ёзилмайди": ("«ilgari», «bo'lgan» so'zlari yozilmaydi", "слова «ранее», «был» не пишутся", "do not write “formerly”, “was”"),
    "иш жойи ва лавозими кўрсатилмаган": ("ish joyi va lavozimi ko'rsatilmagan", "место работы и должность не указаны", "workplace and position not given"),
    "иш жойида қисқартма бор — тўлиқ ёзилсин": ("ish joyida qisqartma bor — to'liq yozilsin", "в месте работы есть сокращение — пишите полностью", "the workplace contains an abbreviation — write it in full"),
    "турар жойи кўрсатилмаган": ("turar joyi ko'rsatilmagan", "место жительства не указано", "residence not given"),
    "турар жойида вилоят, шаҳар, туман номлари тўлиқ кўрсатилсин": ("turar joyida viloyat, shahar, tuman nomlari to'liq ko'rsatilsin", "в месте жительства укажите область, город, район полностью", "give the region, city and district names of the residence in full"),
}
_DYN = [  # (regex, uz, ru, en)
    (r"«(.+)» — «ҳ\.в\.» фақат охирги ёзувда бўлади", "«{0}» — «h.v.» faqat oxirgi yozuvda bo'ladi", "«{0}» — «н.в.» допускается только в последней записи", "“{0}” — “present” is allowed in the last entry only"),
    (r"давр аниқланмади: «(.*)»", "davr aniqlanmadi: «{0}»", "период не распознан: «{0}»", "period not recognized: “{0}”"),
    (r"(\d{4}) ва (\d{4}) йиллар орасида бўшлиқ бор", "{0} va {1} yillar orasida bo'shliq bor", "между {0} и {1} годами есть пропуск", "there is a gap between {0} and {1}"),
    (r"(.+): давр олдингиси билан кесишади", "{0}: davr oldingisi bilan kesishadi", "{0}: период пересекается с предыдущим", "{0}: the period overlaps the previous one"),
]


def tr_msg(msg: str, lang: str) -> str:
    if lang == "cy":
        return msg
    i = _LI[lang] - 1
    if msg in _MSG:
        return _MSG[msg][i]
    for rx, *t in _DYN:
        m = re.fullmatch(rx, msg)
        if m:
            return t[i].format(*[fmt_period(g, lang) if re.fullmatch(r"\d{4}.*(й\.|йй\.|ҳ\.в\.)", g) else g for g in m.groups()])
    return msg


def tr_where(where: str, lang: str) -> str:
    i = _LI[lang]
    if where in _WH:
        return _WH[where][i]
    if lang == "cy":
        return where
    for pref in ("Меҳнат фаолияти ", "Депутатлик "):
        if where.startswith(pref):
            base = _WH["Меҳнат фаолияти"][i] if pref.startswith("Меҳ") else \
                {"uz": "Deputatlik", "ru": "Депутатство", "en": "Elected office"}[lang]
            return f"{base} {fmt_period(where[len(pref):], lang)}"
    m = re.match(r"^(.+?) \((.*)\)$", where)
    if m:
        rel = REL.get(m.group(1))
        name = m.group(2)
        if name == "исмсиз":
            name = {"uz": "ismsiz", "ru": "без имени", "en": "no name"}[lang]
        return f"{rel[_IDX[lang]] if rel else m.group(1)} ({name})"
    return where


def tr_warning(where: str, msg: str, lang: str):
    lang = norm_lang(lang)
    return tr_where(where, lang), tr_msg(msg, lang)

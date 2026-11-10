"use strict";
/* Tillar: uz (lotin), cy (o'zbek kirill), ru, en. Kirill varianti lotin matndan avtomatik olinadi; {…} ichi o'zgarmaydi. */
const LANG_LIST = [["uz", "UZ", "Özbekça"], ["cy", "ЎЗ", "Ўзбекча"], ["ru", "RU", "Русский"], ["en", "EN", "English"]];
const HTML_LANG = { uz: "uz", cy: "uz-Cyrl", ru: "ru", en: "en" };
let LANG = "cy";

function translit(src) {
  const parts = src.split(/(\{[^}]*\}|%[a-z]+%)/);
  return parts.map(p => (p[0] === "{" && p.endsWith("}")) ? p.slice(1, -1) : (p[0] === "%" && p.length > 2) ? p : tr1(p)).join("");
}
function tr1(s) {
  const V = "aeiouAEIOU", map = { a: "а", b: "б", d: "д", f: "ф", g: "г", h: "ҳ", i: "и", j: "ж", k: "к", l: "л", m: "м", n: "н", o: "о", p: "п", q: "қ", r: "р", s: "с", t: "т", u: "у", v: "в", x: "х", y: "й", z: "з" };
  let out = "", i = 0;
  const isApos = c => c === "'" || c === "’" || c === "ʻ" || c === "`";
  const atWordStart = k => k === 0 || !/[A-Za-z'’ʻ`]/.test(s[k - 1]);
  while (i < s.length) {
    const c = s[i], lo = c.toLowerCase(), up = c !== lo, n = (s[i + 1] || ""), nl = n.toLowerCase(), n2 = s[i + 2] || "";
    const cap = (x) => up ? x.toUpperCase() : x;
    const capDi = (x) => (up && (n === nl ? false : true)) ? x.toUpperCase() : up ? x[0].toUpperCase() + x.slice(1) : x;
    if ((lo === "o" || lo === "g") && isApos(n)) { out += cap(lo === "o" ? "ў" : "ғ"); i += 2; continue; }
    if (lo === "s" && nl === "h") { out += cap("ш"); i += 2; continue; }
    if (lo === "c" && nl === "h") { out += cap("ч"); i += 2; continue; }
    if (lo === "y" && nl === "o" && !isApos(n2)) { out += cap("ё"); i += 2; continue; }
    if (lo === "y" && nl === "u") { out += cap("ю"); i += 2; continue; }
    if (lo === "y" && nl === "a") { out += cap("я"); i += 2; continue; }
    if (lo === "y" && nl === "e") { out += cap("е"); i += 2; continue; }
    if (lo === "e") { out += cap(atWordStart(i) ? "э" : "е"); i++; continue; }
    if (isApos(c)) { out += "ъ"; i++; continue; }
    if (map[lo]) { out += cap(map[lo]); i++; continue; }
    out += c; i++;
  }
  return out;
}

const D = {};
function K(key, uz, ru, en, cy) { D[key] = { uz, ru, en, cy: cy || null }; }

/* ---------- kirish sahifasi ---------- */
K("brand", "Andoza", "Андоза", "Andoza", "Андоза");
K("tagline", "Obyektivka tayyorlash endi juda oson!", "Подготовить объективку теперь очень просто!", "Creating an official bio is now easier than ever!", "Объективка тайёрлаш энди жуда осон!");
K("pill", "Namunaga 100% mos", "100% соответствие образцу", "Matches the sample 100%");
K("h1a", "Obyektivka —", "Объективка —", "Obyektivka —", "Объективка —");
K("h1b", "bir bosishda", "в один клик", "in one click");
K("h1c", "standart", "по стандарту", "to standard");
K("lead", "Yangisini yarating, eski faylni yuklang yoki butun papkani bir zumda namunaga keltiring.",
  "Создайте новую, загрузите старый файл или приведите целую папку к образцу за считанные секунды.",
  "Create a new one, upload an old file, or bring a whole folder to the standard in seconds.");
K("f1", "Yangi yaratish", "Создать", "Create new");
K("f2", "Tahrirlash", "Править", "Edit");
K("f3", "Papka → {ZIP}", "Папка → ZIP", "Folder → ZIP");
K("start", "Boshlash", "Начать", "Get started");
K("g1", "1-betda jadval yo'q", "Без таблицы на 1-й стр.", "No table on page 1");
K("g2", "{ҳ.в.} bir chiziqda", "«ҳ.в.» на одной линии", "“ҳ.в.” on one line", "ҳ.в. бир чизиқда");
K("g3", "{Word} · {ZIP}", "Word · ZIP", "Word · ZIP");
K("author", "Murodjon", "Муроджон", "Murodjon", "Муроджон");
K("author_role", "Sayt muallifi", "Автор сайта", "Site author");
K("theme", "Mavzuni almashtirish", "Сменить тему", "Switch theme");
K("langname", "Til", "Язык", "Language");
K("home", "Bosh sahifa", "Главная", "Home");

/* ---------- ilova ---------- */
K("t_new", "Yangi", "Новая", "New");
K("t_edit", "Tahrirlash", "Правка", "Edit");
K("t_batch", "Papka", "Папка", "Folder");
K("e_title", "Eski obyektivkani yuklang", "Загрузите старую объективку", "Upload the old form", "Эски объективкани юкланг");
K("e_hint", "Faylni tashlang yoki matnni joylang. Ma'lumotlar shaklga to'ladi, siz tekshirib yuklab olasiz.",
  "Перетащите файл или вставьте текст. Данные заполнят форму — проверьте и скачайте.",
  "Drop a file or paste text. The data fills the form — review it and download.");
K("drop1", "Faylni shu yerga tashlang", "Перетащите файл сюда", "Drop the file here");
K("drop2", "yoki bosib tanlang ({.docx}, {.doc}, {.txt})", "или нажмите, чтобы выбрать (.docx, .doc, .txt)", "or click to choose (.docx, .doc, .txt)");
K("e_ph", "Yoki obyektivka matnini shu yerga joylang…", "Или вставьте сюда текст объективки…", "Or paste the form text here…", "Ёки объективка матнини шу ерга жойланг…");
K("e_go", "Matndan to'ldirish", "Заполнить из текста", "Fill from text");

K("r_basic", "Asosiy", "Основное", "Basics");
K("r_pers", "Shaxsiy", "Личное", "Personal");
K("r_edu", "Ta'lim", "Образование", "Education");
K("r_work", "Mehnat", "Труд", "Career");
K("r_rel", "Qarindoshlar", "Родные", "Relatives");
K("r_fin", "Yakun", "Итог", "Finish");
K("clear", "Tozalash", "Очистить", "Clear");

K("p_basic", "Asosiy", "Основное", "Basics");
K("photo", "3×4 rasm", "Фото 3×4", "3×4 photo");
K("photo_pick", "Rasm tanlash", "Выбрать фото", "Choose photo");
K("photo_del", "Olib tashlash", "Убрать", "Remove");
K("l_fio", "F.I.Sh. (to'liq)", "Ф.И.О. (полностью)", "Full name");
K("l_position", "Joriy lavozim (tashkilot nomi bilan)", "Текущая должность (с названием организации)", "Current position (with organization)");
K("l_job", "Lavozimga kirishgan sana", "Дата вступления в должность", "Start date in position");
K("datefmt", "KK.OO.YYYY", "ДД.ММ.ГГГГ", "DD.MM.YYYY", "КК.ОО.ЙЙЙЙ");

K("p_pers", "Shaxsiy ma'lumotlar", "Личные данные", "Personal details");
K("l_birth", "Tug'ilgan yili", "Дата рождения", "Date of birth");
K("l_bplace", "Tug'ilgan joyi", "Место рождения", "Place of birth");
K("l_nat", "Millati", "Национальность", "Nationality");
K("l_party", "Partiyaviyligi", "Партийность", "Party affiliation");
K("l_edu", "Ma'lumoti", "Образование", "Education level");
K("l_spec", "Ma'lumoti bo'yicha mutaxassisligi", "Специальность по образованию", "Specialty");
K("l_deg", "Ilmiy darajasi", "Учёная степень", "Academic degree");
K("l_ttl", "Ilmiy unvoni", "Учёное звание", "Academic title");
K("l_mil", "Harbiy (maxsus) unvoni", "Воинское (специальное) звание", "Military (special) rank");
K("l_langs", "Qaysi chet tillarini biladi", "Какими иностранными языками владеет", "Foreign languages");
K("langs_other", "boshqa til (vergul bilan)", "другой язык (через запятую)", "other language (comma-separated)");

K("p_edu", "Ta'lim va mukofotlar", "Образование и награды", "Education & awards");
K("h_grad", "Tamomlagan o'quv yurtlari", "Окончил учебные заведения", "Institutions graduated");
K("add_grad", "+ O'quv yurti", "+ Учебное заведение", "+ Institution");
K("h_award", "Davlat mukofotlari", "Государственные награды", "State awards");
K("empty_none", "(bo'sh = «yo'q»)", "(пусто = «нет»)", "(empty = “none”)");
K("add_award", "+ Mukofot", "+ Награда", "+ Award");
K("h_dep", "Xalq deputatlari / saylanadigan organlar a'zoligi", "Депутат / член выборных органов", "Deputy / elected bodies");
K("add_row", "+ Qator", "+ Строка", "+ Row");
K("ph_year", "Yil", "Год", "Year");
K("ph_inst", "O'quv yurti nomi", "Название учебного заведения", "Institution name");
K("ph_award", "Mukofot nomi", "Название награды", "Award name");

K("p_work", "Mehnat faoliyati", "Трудовая деятельность", "Work history");
K("work_hint", "Davr — yillar. Hozirgi ish uchun «ҳ.в.» belgisini qo'ying. Matn oxirida {Enter} — yangi qator.",
  "Период — годы. Для текущей работы отметьте «ҳ.в.». Enter в конце текста — новая строка.",
  "Period — years. For the current job tick “ҳ.в.” (to present). Enter at the end of the text adds a row.");
K("add_work", "+ Qator qo'shish", "+ Добавить строку", "+ Add row");
K("ph_from", "dan", "с", "from");
K("ph_to", "gacha", "по", "to");
K("ph_org", "Tashkilot va lavozim", "Организация и должность", "Organization and position");
K("raw_chip", "Davr aniqlanmadi: «%raw%» — yillarni kiriting", "Период не распознан: «%raw%» — введите годы", "Period not recognized: “%raw%” — enter the years");

K("p_rel", "Yaqin qarindoshlari", "Ближайшие родственники", "Close relatives");
K("quick", "Tez qo'shish:", "Быстро добавить:", "Quick add:");
K("rel_paste", "Matndan qo'shish ({Word} jadvalidan nusxa yoki erkin matn)", "Добавить из текста (копия из таблицы Word или свободный текст)", "Add from text (copied from a Word table, or free text)");
K("rel_ph", "Har qator — bitta qarindosh. Masalan:\nОтаси | Рахматуллаев Бахтиёр Ахмедович | 1950 йил, Наманган вилояти, Тўрақўрғон тумани | Пенсияда | Наманган вилояти, Тўрақўрғон тумани",
  "Каждая строка — один родственник. Например:\nОтаси | Рахматуллаев Бахтиёр Ахмедович | 1950 йил, Наманган вилояти, Тўрақўрғон тумани | Пенсияда | Наманган вилояти, Тўрақўрғон тумани",
  "One relative per line. For example:\nОтаси | Рахматуллаев Бахтиёр Ахмедович | 1950 йил, Наманган вилояти, Тўрақўрғон тумани | Пенсияда | Наманган вилояти, Тўрақўрғон тумани",
  "Ҳар қатор — битта қариндош. Масалан:\nОтаси | Рахматуллаев Бахтиёр Ахмедович | 1950 йил, Наманган вилояти, Тўрақўрғон тумани | Пенсияда | Наманган вилояти, Тўрақўрғон тумани");
K("rel_add_go", "Qarindoshlarni qo'shish", "Добавить родственников", "Add relatives");
const RELMAP = [
  ["Отаси", "Otasi", "Отец", "Father"], ["Онаси", "Onasi", "Мать", "Mother"],
  ["Акаси", "Akasi", "Старший брат", "Elder brother"], ["Опаси", "Opasi", "Старшая сестра", "Elder sister"],
  ["Укаси", "Ukasi", "Младший брат", "Younger brother"], ["Синглиси", "Singlisi", "Младшая сестра", "Younger sister"],
  ["Турмуш ўртоғи", "Turmush o'rtog'i", "Супруг(а)", "Spouse"], ["Ўғли", "O'g'li", "Сын", "Son"], ["Қизи", "Qizi", "Дочь", "Daughter"],
  ["Қайнотаси", "Qaynotasi", "Тесть / свёкор", "Father-in-law"], ["Қайнонаси", "Qaynonasi", "Тёща / свекровь", "Mother-in-law"],
];
RELMAP.forEach(([c, u, r, e]) => K("rel_" + c, u, r, e));
K("s_works", "Ishlaydi", "Работает", "Works");
K("s_pension", "Pensiyada", "На пенсии", "Retired");
K("s_dead", "Vafot etgan", "Умер(ла)", "Deceased");
K("l_rwork", "Ish joyi va lavozimi", "Место работы и должность", "Workplace and position");
K("l_rwork_old", "Avvalgi ish joyi va lavozimi (qavsda yoziladi)", "Прежнее место работы и должность (пишется в скобках)", "Former workplace and position (written in brackets)");
K("l_dy", "Vafot etgan yili", "Год смерти", "Year of death");
K("l_res", "Turar joyi", "Место жительства", "Residence");
K("ph_rwork", "Tashkilot nomi va lavozimi (qisqartmasiz)", "Организация и должность (без сокращений)", "Organization and position (no abbreviations)");
K("ph_region", "Viloyat, tuman (shahar)", "Область, район (город)", "Region, district (city)");
K("ph_addr", "Viloyat, tuman (shahar), ko'cha", "Область, район (город), улица", "Region, district (city), street");
K("copy_prev", "Oldingisidan nusxa", "Копия с предыдущего", "Copy from previous");
K("del", "O'chirish", "Удалить", "Delete");
K("no_name", "— F.I.Sh. kiritilmagan —", "— Ф.И.О. не указано —", "— name not entered —");
K("sfx_dead", " · vafot etgan", " · умер(ла)", " · deceased");
K("sfx_pension", " · pensiyada", " · на пенсии", " · retired");
K("check_badge", "tekshiring", "проверьте", "check");

K("w_title", "Tekshiruv", "Проверка", "Check");

K("a_login", "Kirish", "Войти", "Sign in");
K("a_logout", "Chiqish", "Выйти", "Sign out");
K("a_admin", "Admin panel", "Админ-панель", "Admin panel");
K("a_title", "Tizimga kiring", "Войдите в систему", "Sign in");
K("a_sub", "{Word} faylni yuklab olish uchun {Google} hisobingiz bilan kiring. Kiritgan ma'lumotlaringiz yo'qolmaydi.", "Чтобы скачать Word-файл, войдите через аккаунт Google. Введённые данные не потеряются.", "Sign in with Google to download the Word file. Your entered data will not be lost.");
K("a_need", "{Word} faylni yuklab olish uchun avval kiring.", "Сначала войдите, чтобы скачать файл.", "Please sign in to download.");
K("a_nocfg", "Google orqali kirish hali sozlanmagan.", "Вход через Google ещё не настроен.", "Google sign-in is not configured yet.");
K("a_cancel", "Kirish bekor qilindi.", "Вход отменён.", "Sign-in cancelled.");
K("a_blocked", "Hisobingiz bloklangan. Admin bilan bog'laning.", "Ваш аккаунт заблокирован. Свяжитесь с админом.", "Your account is blocked. Contact the admin.");
K("a_pending", "Hisobingiz admin tasdig'ini kutmoqda.", "Ваш аккаунт ожидает подтверждения админа.", "Your account is awaiting admin approval.");
K("a_bye", "Chiqildi.", "Вы вышли.", "Signed out.");
K("r_super", "Super admin", "Супер-админ", "Super admin");
K("r_admin", "Admin", "Админ", "Admin");
K("r_user", "Foydalanuvchi", "Пользователь", "User");
K("ad_title", "Admin panel", "Админ-панель", "Admin panel");
K("ad_back", "← Ilovaga", "← В приложение", "← Back to app");
K("ad_total", "Jami foydalanuvchi", "Всего пользователей", "Total users");
K("ad_active", "Hozir faol", "Сейчас онлайн", "Active now");
K("ad_today", "Bugun kirgan", "Заходили сегодня", "Signed in today");
K("ad_dl", "{Word} yuklashlar", "Скачано файлов", "Word downloads");
K("ad_pending", "Tasdiq kutmoqda", "Ждут подтверждения", "Pending approval");
K("ad_blocked", "Bloklangan", "Заблокированы", "Blocked");
K("ad_appr", "Yangi foydalanuvchilarni admin tasdiqlasin", "Новых пользователей подтверждает админ", "Admin must approve new users");
K("ad_addadm", "Admin qo'shish (email)", "Добавить админа (email)", "Add admin (email)");
K("ad_add", "Qo'shish", "Добавить", "Add");
K("ad_logins", "Kirishlar soni", "Количество входов", "Sign-ins");
K("ad_now", "hozir", "сейчас", "now");
K("ad_ago_m", "%n% daq. oldin", "%n% мин. назад", "%n% min ago");
K("ad_ago_h", "%n% soat oldin", "%n% ч. назад", "%n% h ago");
K("ad_ago_d", "%n% kun oldin", "%n% дн. назад", "%n% d ago");
K("ad_block", "Bloklash", "Блокировать", "Block");
K("ad_unblock", "Ochish", "Разблокировать", "Unblock");
K("ad_approve", "Tasdiqlash", "Подтвердить", "Approve");
K("ad_mkadm", "Admin qilish", "Сделать админом", "Make admin");
K("ad_rmadm", "Adminlikdan olish", "Снять админа", "Remove admin");
K("ad_del", "O'chirish", "Удалить", "Delete");
K("ad_confirm_del", "%e% o'chirilsinmi?", "Удалить %e%?", "Delete %e%?");
K("ad_empty", "Hali foydalanuvchi yo'q.", "Пользователей пока нет.", "No users yet.");
K("ad_forbidden", "Bu sahifa faqat adminlar uchun.", "Эта страница только для админов.", "Admins only.");
K("dl_lang", "Hujjat tili", "Язык документа", "Document language");
K("dl_follow", "Dastur tili bilan bir xil", "Как язык программы", "Same as app language");
K("w_empty", "Hali ma'lumot kiritilmagan.", "Данные ещё не введены.", "No data entered yet.");
K("w_ok", "Hammasi standartga mos ✓", "Всё соответствует стандарту ✓", "Everything matches the standard ✓");
K("dl", "{Word} faylni yuklab olish", "Скачать файл Word", "Download Word file");
K("dl_busy", "Tayyorlanmoqda…", "Подготовка…", "Preparing…");
K("dl_done", "Yuklab olindi: ", "Скачано: ", "Downloaded: ");
K("back", "← Orqaga", "← Назад", "← Back");
K("next", "Keyingi →", "Далее →", "Next →");
K("fin_arrow", "Yakun →", "Итог →", "Finish →");

K("b_title", "Papkadagi hammasini standartga keltirish", "Привести всё в папке к стандарту", "Standardize everything in a folder");
K("b_hint", "Bir nechta fayl yoki butun papkani tanlang ({.docx} / {.doc}). Natija — bitta {ZIP}: tayyor fayllar va {hisobot.txt}.",
  "Выберите несколько файлов или целую папку (.docx / .doc). Результат — один ZIP: готовые файлы и hisobot.txt.",
  "Choose several files or a whole folder (.docx / .doc). Result: one ZIP with the finished files and hisobot.txt.");
K("b_files", "Fayllarni tanlash", "Выбрать файлы", "Choose files");
K("b_dir", "Papkani tanlash", "Выбрать папку", "Choose folder");
K("b_go", "Boshlash", "Начать", "Start");
K("b_zip", "{ZIP} yuklab olish", "Скачать ZIP", "Download ZIP");
K("b_sel", "%n% ta fayl tanlandi", "Выбрано файлов: %n%", "%n% files selected");
K("b_none", "Mos fayl topilmadi", "Подходящих файлов нет", "No matching files");
K("b_work", "ishlanmoqda…", "обработка…", "processing…");
K("b_warns", "%n% ta ogohlantirish", "предупреждений: %n%", "%n% warnings");
K("b_err", "XATO: ", "ОШИБКА: ", "ERROR: ");
K("b_done", "Tayyor: %a% / %b%. {ZIP} ni yuklab oling.", "Готово: %a% / %b%. Скачайте ZIP.", "Done: %a% / %b%. Download the ZIP.");

K("m_fio", "Avval F.I.Sh. ni kiriting", "Сначала введите Ф.И.О.", "Enter the full name first");
K("m_warn", "Ogohlantirishlar bor (%n% ta). Baribir yuklab olinsinmi?", "Есть предупреждения (%n%). Всё равно скачать?", "There are %n% warnings. Download anyway?");
K("m_read", "O'qildi. Ma'lumotlarni tekshiring", "Прочитано. Проверьте данные", "Loaded. Please review the data");
K("m_paste", "Matnni joylang", "Вставьте текст", "Paste the text");
K("m_reladd", "%n% ta qarindosh qo'shildi. Tekshiring", "Добавлено родственников: %n%. Проверьте", "%n% relatives added. Please review");
K("m_noprev", "Oldingi qarindosh yo'q", "Нет предыдущего родственника", "No previous relative");
K("m_discard", "Joriy ma'lumot tozalansinmi?", "Очистить текущие данные?", "Clear the current data?");
K("m_clear", "Hamma kiritilganlar tozalansinmi?", "Очистить всё введённое?", "Clear everything entered?");
K("e_net", "Server bilan aloqa yo'q. Server ishlayotganini tekshiring.", "Нет связи с сервером. Проверьте, что сервер запущен.", "Can't reach the server. Check that it is running.");
K("e_auth", "Parol kerak. Sahifani yangilang.", "Нужен пароль. Обновите страницу.", "Password required. Reload the page.");
K("e_gen", "Xatolik (%code%)", "Ошибка (%code%)", "Error (%code%)");

const LGMAP = [["рус", "rus", "русский", "Russian"], ["инглиз", "ingliz", "английский", "English"], ["немис", "nemis", "немецкий", "German"],
  ["француз", "frantsuz", "французский", "French"], ["испан", "ispan", "испанский", "Spanish"], ["итальян", "italyan", "итальянский", "Italian"],
  ["турк", "turk", "турецкий", "Turkish"], ["араб", "arab", "арабский", "Arabic"], ["хитой", "xitoy", "китайский", "Chinese"],
  ["япон", "yapon", "японский", "Japanese"], ["корейс", "koreys", "корейский", "Korean"]];
LGMAP.forEach(([c, u, r, e]) => K("lg_" + c, u, r, e, c));

/* Yangi o'zbek lotin alifbosi: o'→ö, g'→ğ, sh→ş, ch→ç (manba matn eski yozuvda; kirill tarjima shundan olinadi). */
function newAlpha(s) {
  return s.split(/(\{[^}]*\}|%[a-z_]+%)/).map(p => (p[0] === "{" || p[0] === "%") ? p : p
    .replace(/([oO])[ʻʼ'’‘`]/g, (m, c) => c === "o" ? "ö" : "Ö")
    .replace(/([gG])[ʻʼ'’‘`]/g, (m, c) => c === "g" ? "ğ" : "Ğ")
    .replace(/[sS][hH]/g, m => m === "sh" ? "ş" : m === "SH" ? "Ş" : "Ş")
    .replace(/[cC][hH]/g, m => m === "ch" ? "ç" : "Ç")
    .replace(/(\p{L})['’ʻ‘`](?=\p{L})/gu, "$1ʼ")).join("");
}
const CL = { а: "a", б: "b", в: "v", г: "g", д: "d", ё: "yo", ж: "j", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "x", ц: "ts", ч: "ç", ш: "ş", щ: "şç", ъ: "ʼ", ы: "i", ь: "", э: "e", ю: "yu", я: "ya", ў: "ö", қ: "q", ғ: "ğ", ҳ: "h", е: "e" };
function cyrToLat(s) {
  return s.replace(/[А-Яа-яЁёЎўҚқҒғҲҳ]+/g, w => {
    const lo = w.toLowerCase(), all = w.length > 1 && w === w.toUpperCase();
    let out = "";
    for (let i = 0; i < lo.length; i++) {
      let c = lo[i], r;
      if (c === "е") r = (i === 0 || "аеёиоуўэюяыъь".includes(lo[i - 1])) ? "ye" : "e"; else r = CL[c] !== undefined ? CL[c] : c;
      if (w[i] !== lo[i]) r = all ? r.toUpperCase() : r[0].toUpperCase() + r.slice(1);
      out += r;
    }
    return out;
  });
}
function t(key, vars) {
  const e = D[key]; if (!e) return key;
  let s = LANG === "cy" ? (e.cy || translit(e.uz)) : (e[LANG] || e.uz).replace(/\{([^}]*)\}/g, "$1");
  if (LANG === "uz") s = cyrToLat(newAlpha(e.uz.replace(/\{([^}]*)\}/g, "$1")));
  if (vars) for (const k in vars) s = s.split("%" + k + "%").join(vars[k]);
  return s;
}
function applyI18n(root) {
  root = root || document;
  const all = (sel) => { const a = [...root.querySelectorAll(sel)]; if (root.matches && root.matches(sel)) a.unshift(root); return a; };
  all("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  all("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  all("input[placeholder],textarea[placeholder]").forEach(el => {
    if (el.dataset.i18nPh) return;
    if (el.dataset.ph0 === undefined) el.dataset.ph0 = el.getAttribute("placeholder");
    el.placeholder = LANG === "uz" ? cyrToLat(el.dataset.ph0) : el.dataset.ph0;
  });
  all("datalist option").forEach(o => {
    if (o.dataset.v0 === undefined) o.dataset.v0 = o.value;
    o.value = LANG === "uz" ? cyrToLat(o.dataset.v0) : o.dataset.v0;
  });
  all("[data-i18n-aria]").forEach(el => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); el.title = t(el.dataset.i18nAria); });
}
function detectLang() {
  let l = null;
  try { l = localStorage.getItem("lang"); } catch (e) {}
  if (D && LANG_LIST.some(x => x[0] === l)) return l;
  return "cy";
}

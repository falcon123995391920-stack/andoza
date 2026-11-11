"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const L = (k, v) => t(k, v);
function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
  return e;
}
const sp = (key, cls) => h("span", { "data-i18n": key, class: cls || null });       // tarjima qilinadigan matn
const LANGS = ["рус", "инглиз", "немис", "француз", "испан", "итальян", "турк", "араб", "хитой", "япон", "корейс"];
const RELS = ["Отаси", "Онаси", "Акаси", "Опаси", "Укаси", "Синглиси", "Турмуш ўртоғи", "Ўғли", "Қизи", "Қайнотаси", "Қайнонаси"];
const SIMPLE = ["fio", "position", "birth_date", "birth_place", "nationality", "party", "education",
  "specialty", "degree", "title", "military", "langs_other", "job_date"];
const STEPS = 5;                       // 0..4 = bo'limlar, 5 = yakun (faqat telefonda)
let JOBRAW = "", photoData = "", uid = 0, step = 0, mode = "new", loaded = false, dirtyFlag = false, lastWarn = { ws: [], empty: true };

function toast(msg, ms = 3500) {
  const el = $("#toast"); el.textContent = msg; el.classList.remove("hidden");
  clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.add("hidden"), ms);
}

/* ---------------- mavzu ---------------- */
const SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>';
function applyTheme(th) {
  document.documentElement.setAttribute("data-theme", th);
  try { localStorage.setItem("theme", th); } catch (e) {}
  $$(".theme-btn").forEach(b => { b.innerHTML = th === "dark" ? SUN : MOON; });
  const m = $("meta[name=theme-color]"); if (m) m.content = th === "dark" ? "#000000" : "#f2f2f7";
}

/* ---------------- til ---------------- */
function buildLangMenus() {
  $$(".lang-slot").forEach(slot => {
    slot.replaceChildren();
    const btn = h("button", { class: "icon-btn lang-btn", type: "button", "data-i18n-aria": "langname", "aria-haspopup": "true" });
    const menu = h("div", { class: "menu hidden", role: "menu" }, LANG_LIST.map(([c, code, name]) =>
      h("button", { type: "button", "data-lang": c, role: "menuitem", onclick: () => { setLang(c); menu.classList.add("hidden"); } }, name, h("i", { text: code }))));
    btn.addEventListener("click", e => { e.stopPropagation(); const o = menu.classList.contains("hidden"); closeMenus(); menu.classList.toggle("hidden", !o); });
    slot.append(h("div", { class: "lang" }, btn, menu));
  });
}
function closeMenus() { $$(".menu").forEach(m => m.classList.add("hidden")); }
function setLang(l, silent) {
  LANG = l;
  try { localStorage.setItem("lang", l); } catch (e) {}
  document.documentElement.lang = HTML_LANG[l];
  const code = LANG_LIST.find(x => x[0] === l)[1];
  $$(".lang-btn").forEach(b => { b.textContent = code; });
  $$(".menu button").forEach(b => b.classList.toggle("on", b.dataset.lang === l));
  document.title = L("brand");
  applyI18n(document);
  $$(".lang-btn").forEach(b => { b.textContent = code; b.title = L("langname"); });
  $$("#rel-rows .rel").forEach(c => { relTitle(c); relLabels(c); });
  $$(".chip[data-raw]").forEach(c => { c.textContent = L("raw_chip", { raw: c.dataset.raw }); });
  buildDocLang();
  renderWarn(lastWarn.ws, lastWarn.empty);
  if (typeof runCheck === "function" && !lastWarn.empty) runCheck();
  updNav();
  if (typeof authLang === "function") authLang();
}

/* ---------------- yordamchilar ---------------- */
function fmtDate(v) {
  const d = v.replace(/\D/g, "").slice(0, 8);
  let o = d.slice(0, 2);
  if (d.length > 2) o += "." + d.slice(2, 4);
  if (d.length > 4) o += "." + d.slice(4);
  return o;
}
const MON = ["январдан", "февралдан", "мартдан", "апрелдан", "майдан", "июндан", "июлдан", "августдан", "сентябрдан", "октябрдан", "ноябрдан", "декабрдан"];
function jobPreview() {
  const v = $("#job_date").value, m = v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  const ok = m && +m[2] >= 1 && +m[2] <= 12 && +m[1] >= 1 && +m[1] <= 31;
  const p = $("#job_preview");
  p.classList.toggle("bad", !!v && !ok);
  p.textContent = ok ? `${m[3]} йил ${+m[1]} ${MON[+m[2] - 1]}:` : v ? "?" : JOBRAW;
}
function grow(el) { if (!el.offsetParent) return; el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight + 2, 300) + "px"; }
function markDirty() { dirtyFlag = true; }
function done(el) { applyI18n(el); return el; }

/* ---------------- qatorlar ---------------- */
function delBtn(row) { return h("button", { class: "x", type: "button", "data-i18n-aria": "del", onclick: () => { row.remove(); changed(); } }, "×"); }
function ynRow(box, v = {}, phKey = "") {
  const row = h("div", { class: "row" });
  const y = h("input", { class: "y", inputmode: "numeric", maxlength: 4, "data-i18n-ph": "ph_year", value: v.year || "" });
  const n = h("input", { class: "n", "data-i18n-ph": phKey, value: v.name || "" });
  n.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); $(".y", ynRow(box, {}, phKey)).focus(); } });
  row.append(y, n, delBtn(row));
  box.append(row); return done(row);
}
function workRow(box, v = {}) {
  const row = h("div", { class: "row work" });
  const a = h("input", { class: "a", inputmode: "numeric", maxlength: 4, "data-i18n-ph": "ph_from", value: v.from || "" });
  const b = h("input", { class: "b", inputmode: "numeric", maxlength: 4, "data-i18n-ph": "ph_to", value: v.to || "" });
  const pid = "p" + (++uid);
  const cb = h("input", { type: "checkbox", class: "pr", id: pid }); cb.checked = !!v.present;
  const ph = h("label", { class: "ph", for: pid }, cb, "ҳ.в.");
  const ta = h("textarea", { class: "t", rows: 1, "data-i18n-ph": "ph_org" }); ta.value = v.text || "";
  const sync = () => { b.disabled = cb.checked; if (cb.checked) b.value = ""; };
  cb.addEventListener("change", () => {
    sync();
    if (cb.checked) {                       // "ҳ.в." bitta bo'ladi va doim eng pastda turadi
      $$(".row.work", box).forEach(r => { const o = $(".pr", r); if (o !== cb && o.checked) { o.checked = false; $(".b", r).disabled = false; } });
      box.append(row); setTimeout(() => grow(ta), 0);
    }
  });
  sync();
  ta.addEventListener("input", () => grow(ta));
  ta.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $(".a", workRow(box)).focus(); }
  });
  const raw = h("input", { type: "hidden", class: "raw", value: v.raw || "" });
  row.append(a, b, ph, ta, delBtn(row), raw);
  if (v.raw) row.append(h("div", { class: "chip", "data-raw": v.raw, text: L("raw_chip", { raw: v.raw }) }));
  const last = $$(".row.work", box).find(r => $(".pr", r).checked);
  if (last && !cb.checked) box.insertBefore(row, last); else box.append(row);      // yangi qator "ҳ.в." dan oldin qo'shiladi
  setTimeout(() => grow(ta), 0); return done(row);
}
function relTitle(card) {
  const s = $("input[type=radio]:checked", card).value;
  const st = s === "dead" ? L("sfx_dead") : s === "pension" ? L("sfx_pension") : "";
  $(".rt", card).textContent = L("rel_" + card.sel.value);
  $(".rn", card).textContent = ($("input.fio", card).value || L("no_name")) + st;
}
function relLabels(card) {
  const s = $("input[type=radio]:checked", card).value;
  const wl = $(".wl", card); wl.dataset.i18n = s === "works" ? "l_rwork" : "l_rwork_old"; wl.textContent = L(wl.dataset.i18n);
}
function relCard(v = {}, open = true) {
  const id = "r" + (++uid);
  const sel = h("select", { class: "rel-sel", "data-i18n-aria": "quick" }, RELS.map(r => h("option", { value: r, "data-i18n": "rel_" + r })));
  const card = h("div", { class: "rel" });
  const mk = (cls, labKey, val, phKey = "", attrs = {}) =>
    h("label", { class: "f " + cls }, sp(labKey), h("input", { class: cls, value: val || "", "data-i18n-ph": phKey || null, ...attrs }));
  const st = v.status || "works";
  const radios = [["works", "s_works"], ["pension", "s_pension"], ["dead", "s_dead"]].map(([k, l]) =>
    h("label", {}, h("input", { type: "radio", name: id, value: k, ...(k === st ? { checked: true } : {}) }), " ", sp(l)));
  const wl = sp("l_rwork", "wl");
  const workLab = h("label", { class: "f w" }, wl, h("textarea", { class: "work", rows: 2, "data-i18n-ph": "ph_rwork" }));
  $(".work", workLab).value = v.work || "";
  const dead = mk("dy", "l_dy", v.death_year, "", { inputmode: "numeric", maxlength: 4, "data-i18n-ph": "ph_year4" });
  const res = mk("res", "l_res", v.residence, "ph_addr");
  if (v.relation && !RELS.includes(v.relation)) sel.append(h("option", { value: v.relation, text: v.relation }));
  sel.value = v.relation || "Отаси"; card.sel = sel;
  const upd = () => {
    const s = $("input[type=radio]:checked", card).value;
    dead.classList.toggle("hidden", s !== "dead");
    res.classList.toggle("hidden", s === "dead");
    relLabels(card); relTitle(card);
  };
  const sum = h("div", { class: "rel-sum", tabindex: 0, role: "button" },
    h("span", { class: "rt" }), h("span", { class: "rn" }), v.auto ? sp("check_badge", "auto") : null,
    h("span", { class: "ch", text: "›" }));
  const toggle = () => {
    const was = card.classList.contains("open");
    $$("#rel-rows .rel").forEach(c => c.classList.remove("open"));
    card.classList.toggle("open", !was);
  };
  sum.addEventListener("click", toggle);
  sum.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  const body = h("div", { class: "rel-body" }, sel,
    h("div", { class: "grid2" },
      mk("fio", "l_fio", v.fio, "", { "data-i18n-ph": "ph_fio", autocapitalize: "words" }),
      mk("by", "l_birth", v.year, "", { inputmode: "numeric", maxlength: 4, "data-i18n-ph": "ph_year4" })),
    h("label", { class: "f" }, sp("l_bplace"), h("input", { class: "bp", value: v.place || "", "data-i18n-ph": "ph_region" })),
    h("div", { class: "stat" }, radios), workLab,
    h("div", {}, dead, res),
    h("div", { class: "rel-act" },
      h("button", { class: "btn small", type: "button", "data-i18n": "copy_prev", onclick: () => {
        const prev = card.previousElementSibling; if (!prev) return toast(L("m_noprev"));
        $(".bp", card).value = $(".bp", prev).value; $("input.res", card).value = $("input.res", prev).value; changed();
      } }),
      h("button", { class: "btn small ghost", type: "button", "data-i18n": "del", onclick: () => { card.remove(); changed(); } })));
  card.append(sum, body);
  card.addEventListener("change", upd);
  card.addEventListener("input", () => relTitle(card));
  const wk = $(".work", workLab); wk.addEventListener("input", () => grow(wk));
  if (open) { $$("#rel-rows .rel").forEach(c => c.classList.remove("open")); card.classList.add("open"); }
  $("#rel-rows").append(card); done(card); upd(); setTimeout(() => grow(wk), 0); return card;
}
function relRead(card) {
  return {
    relation: card.sel.value, fio: $("input.fio", card).value,
    year: $("input.by", card).value, place: $(".bp", card).value,
    status: $("input[type=radio]:checked", card).value,
    death_year: $("input.dy", card).value, work: $("textarea.work", card).value,
    residence: $("input.res", card).value,
  };
}

/* ---------------- yig'ish / to'ldirish ---------------- */
function collect() {
  const w = {};
  for (const k of SIMPLE) w[k] = $("#" + k).value;
  w.job_since = JOBRAW;
  w.langs = $$("#langs input:checked").map(i => i.value);
  w.graduated = $$("#grad-rows .row").map(r => ({ year: $(".y", r).value, name: $(".n", r).value }));
  w.award_rows = $$("#award-rows .row").map(r => ({ year: $(".y", r).value, name: $(".n", r).value }));
  const hist = box => $$(box + " .row").map(r => ({ from: $(".a", r).value, to: $(".b", r).value,
    present: $(".pr", r).checked, raw: $(".raw", r).value, text: $(".t", r).value }));
  w.deputy = hist("#deputy-rows"); w.work = hist("#work-rows");
  w.relatives = $$("#rel-rows .rel").map(relRead);
  return w;
}
function hasData(w) { return !!(w.fio.trim() || w.work.some(r => r.text.trim()) || w.relatives.some(r => r.fio.trim())); }
function fill(w) {
  JOBRAW = w.job_date ? "" : (w.job_since || "");
  for (const k of SIMPLE) $("#" + k).value = w[k] || "";
  $$("#langs input").forEach(i => { i.checked = (w.langs || []).includes(i.value); });
  for (const [box, list, ph] of [["#grad-rows", w.graduated, "ph_inst"], ["#award-rows", w.award_rows, "ph_award"]]) {
    $(box).replaceChildren();
    (list && list.length ? list : [{}]).forEach(v => ynRow($(box), v, ph));
  }
  $("#deputy-rows").replaceChildren(); (w.deputy || []).forEach(v => workRow($("#deputy-rows"), v));
  $("#work-rows").replaceChildren(); (w.work && w.work.length ? w.work : [{}]).forEach(v => workRow($("#work-rows"), v));
  $("#rel-rows").replaceChildren(); (w.relatives || []).forEach(r => relCard(r, false));
  $$("#position,#form textarea").forEach(grow);
  jobPreview(); changed();
}
function resetForm() {
  setPhoto(""); fill({ graduated: [{}], award_rows: [], deputy: [], work: [{}], relatives: [] });
  dirtyFlag = false; $("#dl-msg").textContent = "";
}

/* ---------------- tekshiruv ---------------- */
let timer = 0, seq = 0, warnCount = 0;
function changed() { markDirty(); clearTimeout(timer); timer = setTimeout(runCheck, 450); progress(); }
const DOC_PATHS = ["/api/build", "/api/convert", "/api/zip"];
function docLang() {
  let v = ""; try { v = localStorage.getItem("doclang") || ""; } catch (e) {}
  return LANG_LIST.some(x => x[0] === v) ? v : LANG;
}
function buildDocLang() {
  let v = ""; try { v = localStorage.getItem("doclang") || ""; } catch (e) {}
  $$(".doclang").forEach(sel => {
    sel.replaceChildren(h("option", { value: "", text: L("dl_follow") }),
      ...LANG_LIST.map(([c, , name]) => h("option", { value: c, text: name })));
    sel.value = LANG_LIST.some(x => x[0] === v) ? v : "";
    sel.onchange = () => {
      try { localStorage.setItem("doclang", sel.value); } catch (e) {}
      $$(".doclang").forEach(o => { o.value = sel.value; });
    };
  });
}
async function api(path, body) {
  body = Object.assign({ lang: DOC_PATHS.includes(path) ? docLang() : LANG }, body);
  let r;
  try { r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }
  catch (e) { throw new Error(L("e_net")); }
  if ((r.status === 401 || r.status === 403) && typeof handleAuthFail === "function") {
    if (await handleAuthFail(r)) return api(path, body);
  }
  if (r.status === 401) throw new Error(L("e_auth"));
  if (!r.ok) { let m = L("e_gen", { code: r.status }); try { m = (await r.json()).error || m; } catch (e) {} throw new Error(m); }
  return r;
}
async function runCheck() {
  const me = ++seq, w = collect();
  if (!hasData(w)) { renderWarn([], true); return; }
  try {
    const j = await (await api("/api/check", { person: w })).json();
    if (me === seq) renderWarn(j.warnings);
  } catch (e) { /* jim */ }
}
function renderWarn(ws, empty) {
  lastWarn = { ws, empty: !!empty }; warnCount = ws.length;
  const c = $("#wcount"); c.textContent = empty ? "0" : String(ws.length); c.classList.toggle("has", ws.length > 0);
  $("#warn").replaceChildren(empty ? done(h("p", { class: "ok", "data-i18n": "w_empty" })) :
    ws.length ? h("ul", {}, ws.map(x => warnItem(x))) : done(h("p", { class: "ok", "data-i18n": "w_ok" })));
  $("#fin-cnt").textContent = ws.length ? ` (${ws.length})` : "";
}
function warnItem(x) {
  const go = () => jumpTo(x);
  const li = h("li", { class: x.target ? "go" : "", tabindex: x.target ? 0 : null, role: x.target ? "button" : null },
    h("b", { text: x.where }), x.msg, x.target ? h("span", { class: "arr", text: "›" }) : null);
  if (x.target) {
    li.addEventListener("click", go);
    li.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  }
  return li;
}
function normName(s) { return (s || "").replace(/\s+/g, " ").trim().toLowerCase(); }
function flash(el) {
  if (!el) return;
  const box = el.closest("label,.rel,.row,fieldset") || el;
  box.classList.remove("flash"); void box.offsetWidth; box.classList.add("flash");
  setTimeout(() => box.classList.remove("flash"), 2200);
}
function jumpTo(x) {
  const tg = x.target; if (!tg) return;
  goStep(tg.step, false);
  setTimeout(() => {
    let el = null;
    if (tg.sel) el = $(tg.sel);
    else if (tg.list) { const r = $$(`#${tg.list}-rows .row`)[tg.idx]; el = r && $(".t", r); }
    else if (tg.rel) {
      const cards = $$("#rel-rows .rel");
      const exact = cards.filter(c => c.sel.value === tg.rel.relation && normName($("input.fio", c).value) === normName(tg.rel.fio));
      const card = exact[0] || cards.find(c => c.sel.value === tg.rel.relation);
      if (card) {
        cards.forEach(c => c.classList.remove("open")); card.classList.add("open");
        const m = x.msg;
        el = /Ф\.И\.Ш/.test(m) ? $("input.fio", card)
          : /қариндошлиги|қариндошлик/.test(m) ? card.sel
          : /туғилган йили/.test(m) ? $("input.by", card)
          : /туғилган жойи/.test(m) ? $(".bp", card)
          : /турар жой/.test(m) ? $("input.res", card)
          : $("textarea.work", card);
        if (/Ф\.И\.Ш/.test(m) || /қариндошлик/.test(m)) { /* aynan shu maydon */ }
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        el.focus({ preventScroll: true }); flash(el); return;
      }
    }
    if (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); el.focus({ preventScroll: true }); flash(el); }
  }, 60);
}
function progress() {
  const w = collect(), ok = [
    w.fio.trim() && w.position.trim(),
    w.birth_date.trim() && w.birth_place.trim() && w.nationality.trim() && w.education.trim() && w.specialty.trim(),
    w.graduated.some(g => g.name.trim()),
    w.work.some(r => r.text.trim()),
    w.relatives.length > 0,
  ];
  ok.forEach((v, i) => $(`.rs[data-step='${i}']`).classList.toggle("done", !!v));
}

/* ---------------- bosqichlar ---------------- */
function mobile() { return window.matchMedia("(max-width:900px)").matches; }
function updNav() {
  const last = mobile() ? STEPS : STEPS - 1;
  $("#prev").disabled = step === 0;
  $("#next").disabled = step >= last;
  const n = $("#next"); n.dataset.i18n = (step === STEPS - 1 && mobile()) ? "fin_arrow" : "next"; n.textContent = L(n.dataset.i18n);
}
function goStep(n, focus = true) {
  step = Math.max(0, Math.min(mobile() ? STEPS : STEPS - 1, n));
  $$(".pane").forEach(p => p.classList.toggle("on", +p.dataset.pane === step));
  $$(".rs").forEach(b => b.classList.toggle("on", +b.dataset.step === step));
  $("#editor").classList.toggle("fin", step === STEPS);
  $$("#dots i").forEach((d, i) => d.classList.toggle("on", i === step));
  updNav();
  $("#form").scrollTop = 0;
  $$(`.pane[data-pane='${step}'] textarea`).forEach(grow);
  const cur = $(`.rs[data-step='${step}']`); cur && cur.scrollIntoView && cur.scrollIntoView({ inline: "center", block: "nearest" });
  if (focus && !mobile() && step < STEPS) { const i = $(`.pane[data-pane='${step}'] input:not([type=hidden]):not([type=checkbox]):not([type=radio]), .pane[data-pane='${step}'] textarea`); i && i.focus({ preventScroll: true }); }
}

/* ---------------- rasm ---------------- */
function setPhoto(url) {
  photoData = url;
  const b = $("#photo-box");
  b.style.backgroundImage = url ? `url("${url}")` : "";
  b.firstElementChild && b.firstElementChild.classList.toggle("hidden", !!url);
  $("#photo-del").classList.toggle("hidden", !url);
}
function readAsDataURL(f) { return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(f); }); }

/* ---------------- yuklab olish ---------------- */
async function download() {
  const w = collect();
  if (!w.fio.trim()) { toast(L("m_fio")); goStep(0); return; }
  await runCheck();
  if (warnCount && !confirm(L("m_warn", { n: warnCount }))) return;
  const btn = $("#download"); btn.disabled = true; btn.dataset.i18n = "dl_busy"; btn.textContent = L("dl_busy");
  try {
    const r = await api("/api/build", { person: w, photo: photoData || undefined });
    const name = decodeURIComponent(r.headers.get("X-Filename") || "obyektivka.docx");
    save(await r.blob(), name);
    $("#dl-msg").textContent = L("dl_done") + name; dirtyFlag = false;
  } catch (e) { toast(e.message, 6000); }
  btn.disabled = false; btn.dataset.i18n = "dl"; btn.textContent = L("dl");
}
function save(blob, name) {
  const a = h("a", { href: URL.createObjectURL(blob), download: name });
  document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

/* ---------------- tahrirlash ---------------- */
async function loadParsed(body) {
  try {
    const j = await (await api("/api/parse", body)).json();
    fill(j.person); setPhoto(j.photo || "");
    loaded = true; dirtyFlag = false; showMode();
    renderWarn(j.warnings); goStep(0, false);
    toast(L("m_read"));
  } catch (e) { toast(e.message, 6000); }
}
async function editFile(f) { if (f) loadParsed({ filename: f.name, data: await readAsDataURL(f) }); }

/* ---------------- ommaviy ---------------- */
let bFiles = [], bItems = [];
function bSet(list) {
  bFiles = [...list].filter(f => /\.(docx|doc)$/i.test(f.name) && !f.name.startsWith("~$"));
  $("#b-info").textContent = bFiles.length ? L("b_sel", { n: bFiles.length }) : L("b_none");
  $("#b-go").disabled = !bFiles.length; $("#b-zip").disabled = true; $("#b-list").replaceChildren(); bItems = [];
  $("#b-bar").classList.add("hidden");
}
async function bRun() {
  $("#b-go").disabled = true; $("#b-zip").disabled = true; bItems = [];
  const list = $("#b-list"); list.replaceChildren();
  const bar = $("#b-bar"), inn = $("#b-bar-in"); bar.classList.remove("hidden"); inn.style.width = "0";
  for (let i = 0; i < bFiles.length; i++) {
    const f = bFiles[i], li = h("li", {}, f.name, h("small", { text: L("b_work") })); list.append(li);
    li.scrollIntoView({ block: "nearest" });
    try {
      const j = await (await api("/api/convert", { filename: f.name, data: await readAsDataURL(f) })).json();
      bItems.push({ name: f.name, out: j.out, docx: j.docx, warnings: j.warnings });
      li.className = j.warnings.length ? "w" : "ok";
      li.lastChild.textContent = "→ " + j.out + (j.warnings.length ? " · " + L("b_warns", { n: j.warnings.length }) : " · OK");
      j.warnings.forEach(x => li.append(h("small", { text: "• " + x.where + ": " + x.msg })));
    } catch (e) {
      bItems.push({ name: f.name, error: e.message });
      li.className = "e"; li.lastChild.textContent = L("b_err") + e.message;
    }
    inn.style.width = Math.round((i + 1) / bFiles.length * 100) + "%";
  }
  const okN = bItems.filter(x => !x.error).length;
  $("#b-info").textContent = L("b_done", { a: okN, b: bFiles.length });
  $("#b-go").disabled = false; $("#b-zip").disabled = !okN;
}
async function bZip() {
  try { const r = await api("/api/zip", { items: bItems }); save(await r.blob(), "obyektivkalar.zip"); }
  catch (e) { toast(e.message); }
}

/* ---------------- rejim va sahifalar ---------------- */
function showMode() {
  $$("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === mode));
  $("#edit-loader").classList.toggle("hidden", !(mode === "edit" && !loaded));
  $("#batch").classList.toggle("hidden", mode !== "batch");
  $("#editor").classList.toggle("hidden", mode === "batch" || (mode === "edit" && !loaded));
}
function setMode(m) {
  if (m === mode) return;
  const wasForm = mode !== "batch", toForm = m !== "batch";
  if (wasForm && toForm && hasData(collect()) && dirtyFlag && !confirm(L("m_discard"))) return;
  if (wasForm && toForm) { resetForm(); loaded = false; }
  mode = m; showMode();
  if (m === "new") goStep(0, false);
}
function route() {
  const adm = location.hash === "#admin" || location.hash === "#super", app = location.hash === "#app";
  $("#landing").classList.toggle("on", !app && !adm);
  $("#app").classList.toggle("on", app);
  $("#admin").classList.toggle("on", adm);
  if (typeof showAdmin === "function") showAdmin(adm);
  if (app) goStep(step, false);
}

function init() {
  applyTheme(document.documentElement.getAttribute("data-theme") || "light");
  $$(".theme-btn").forEach(b => b.addEventListener("click", () =>
    applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark")));
  buildLangMenus();
  document.addEventListener("click", closeMenus);
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeMenus(); });
  $("#langs").append(...LANGS.map(l => h("label", {}, h("input", { type: "checkbox", value: l }), sp("lg_" + l))));
  $("#rel-quick").append(...RELS.map(r => h("button", { class: "btn small", type: "button", onclick: () => {
    const c = relCard({ relation: r }); $("input.fio", c).focus(); changed(); } }, "+ ", sp("rel_" + r))));
  $("#dots").append(...Array.from({ length: STEPS }, () => h("i")));
  $$("[data-add]").forEach(b => b.addEventListener("click", () => {
    const k = b.dataset.add;
    if (k === "grad") $(".y", ynRow($("#grad-rows"), {}, "ph_inst")).focus();
    if (k === "award") $(".y", ynRow($("#award-rows"), {}, "ph_award")).focus();
    if (k === "deputy") $(".a", workRow($("#deputy-rows"))).focus();
    if (k === "work") $(".a", workRow($("#work-rows"))).focus();
  }));
  $$("#tabs button").forEach(b => b.addEventListener("click", () => setMode(b.dataset.tab)));
  $$(".rs").forEach(b => b.addEventListener("click", () => goStep(+b.dataset.step)));
  $("#prev").addEventListener("click", () => goStep(step - 1));
  $("#next").addEventListener("click", () => goStep(step + 1));
  window.addEventListener("resize", () => { if (!mobile() && step === STEPS) goStep(STEPS - 1, false); else goStep(step, false); });
  $("#clear").addEventListener("click", () => { if (!hasData(collect()) || confirm(L("m_clear"))) { resetForm(); goStep(0); } });
  $$(".date").forEach(i => i.addEventListener("input", () => { i.value = fmtDate(i.value); jobPreview(); }));
  $("#form").addEventListener("input", changed);
  $("#form").addEventListener("change", changed);
  $$("#form textarea").forEach(ta => ta.addEventListener("input", () => grow(ta)));
  $("#photo-pick").addEventListener("click", () => $("#photo-file").click());
  $("#photo-del").addEventListener("click", () => { setPhoto(""); markDirty(); });
  $("#photo-file").addEventListener("change", async e => { const f = e.target.files[0]; if (f) { setPhoto(await readAsDataURL(f)); markDirty(); } e.target.value = ""; });
  $("#download").addEventListener("click", download);
  const drop = $("#drop");
  $("#edit-file").addEventListener("change", e => { editFile(e.target.files[0]); e.target.value = ""; });
  ["dragover", "dragenter"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => editFile(e.dataTransfer.files[0]));
  $("#edit-text-go").addEventListener("click", () => {
    const tx = $("#edit-text").value.trim(); if (!tx) return toast(L("m_paste"));
    loadParsed({ text: tx });
  });
  $("#rel-text-go").addEventListener("click", async () => {
    const tx = $("#rel-text").value.trim(); if (!tx) return toast(L("m_paste"));
    try {
      const r = await (await api("/api/relatives", { text: tx })).json();
      r.relatives.forEach(x => relCard(x, false)); $("#rel-text").value = ""; changed();
      toast(L("m_reladd", { n: r.relatives.length }));
    } catch (e) { toast(e.message); }
  });
  $("#b-files").addEventListener("change", e => bSet(e.target.files));
  $("#b-dir").addEventListener("change", e => bSet(e.target.files));
  $("#b-go").addEventListener("click", bRun);
  $("#b-zip").addEventListener("click", bZip);
  window.addEventListener("beforeunload", e => { if (dirtyFlag && hasData(collect())) { e.preventDefault(); e.returnValue = ""; } });
  window.addEventListener("hashchange", route);
  LANG = detectLang();
  resetForm(); showMode(); goStep(0, false); setLang(LANG); route();
  if (typeof authInit === "function") authInit();
}
document.addEventListener("DOMContentLoaded", init);

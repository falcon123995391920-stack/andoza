"use strict";
/* Kirish (Google), foydalanuvchi tugmasi va admin panel. app.js dan keyin yuklanadi. */
let ME = null, CFG = { google_client_id: "", dev: false }, loginWait = null, gsiLoaded = false, adminTimer = null, adminData = null;

async function getJSON(path) { const r = await fetch(path); return r.json(); }
async function postJSON(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  let j = {}; try { j = await r.json(); } catch (e) {}
  if (!r.ok) { const e = new Error(j.error || L("e_gen", { code: r.status })); e.auth = j.auth; e.status = r.status; throw e; }
  return j;
}
const isAdmin = () => !!ME && (ME.role === "admin" || ME.role === "super");

/* ---------- foydalanuvchi tugmasi ---------- */
function renderUser() {
  $$(".user-slot").forEach(slot => {
    slot.replaceChildren();
    if (!ME) {
      slot.append(h("button", { class: "btn small", type: "button", onclick: () => askLogin().catch(() => {}) }, L("a_login")));
      return;
    }
    const av = ME.picture ? h("img", { class: "ava", src: ME.picture, alt: "", referrerpolicy: "no-referrer", width: 32, height: 32 })
                          : h("span", { class: "ava ph" }, (ME.name || ME.email)[0].toUpperCase());
    const menu = h("div", { class: "menu umenu hidden" },
      h("div", { class: "uinfo" }, h("b", { text: ME.name || ME.email }), h("small", { text: ME.email }), h("small", { class: "rolechip", text: L("r_" + ME.role) })),
      isAdmin() ? h("button", { type: "button", onclick: () => { menu.classList.add("hidden"); location.hash = "#admin"; } }, L("a_admin")) : null,
      h("button", { type: "button", onclick: logout }, L("a_logout")));
    const btn = h("button", { class: "icon-btn ubtn", type: "button", "aria-label": ME.email, onclick: e => { e.stopPropagation(); menu.classList.toggle("hidden"); } }, av);
    slot.append(btn, menu);
  });
}
document.addEventListener("click", () => $$(".umenu").forEach(m => m.classList.add("hidden")));

async function loadMe() {
  try { ME = (await getJSON("/api/me")).user; } catch (e) { ME = null; }
  renderUser();
}
async function logout() {
  try { await postJSON("/api/auth/logout"); } catch (e) {}
  ME = null; renderUser();
  if (location.hash === "#admin") location.hash = "#app";
  toast(L("a_bye"));
}

/* ---------- kirish oynasi ---------- */
function loadGsi() {
  if (gsiLoaded) return Promise.resolve();
  return new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client"; s.async = true;
    s.onload = () => { gsiLoaded = true; res(); }; s.onerror = () => rej(new Error("gsi"));
    document.head.append(s);
  });
}
function closeLogin(ok, err) {
  $("#login").classList.add("hidden");
  const w = loginWait; loginWait = null;
  if (w) (ok ? w.res() : w.rej(err || new Error(L("a_cancel"))));
}
async function onGoogle(resp) {
  try {
    ME = (await postJSON("/api/auth/google", { credential: resp.credential })).user;
    renderUser(); closeLogin(true);
  } catch (e) { $("#login-msg").textContent = e.message; }
}
function askLogin(msgKey) {
  if (ME) return Promise.resolve();
  if (loginWait) return loginWait.p;
  const box = $("#login"); box.classList.remove("hidden");
  $("#login-msg").textContent = msgKey ? L(msgKey) : "";
  const slot = $("#g-btn"); slot.replaceChildren();
  $("#login-dev").classList.toggle("hidden", !CFG.dev);
  if (CFG.google_client_id) {
    loadGsi().then(() => {
      google.accounts.id.initialize({ client_id: CFG.google_client_id, callback: onGoogle, ux_mode: "popup" });
      google.accounts.id.renderButton(slot, { theme: document.documentElement.dataset.theme === "dark" ? "filled_black" : "outline",
        size: "large", shape: "pill", text: "continue_with", width: 280, locale: { uz: "uz", cy: "uz", ru: "ru", en: "en" }[LANG] });
    }).catch(() => { $("#login-msg").textContent = L("e_net"); });
  } else if (!CFG.dev) $("#login-msg").textContent = L("a_nocfg");
  let res, rej; const p = new Promise((a, b) => { res = a; rej = b; });
  loginWait = { p, res, rej };
  return p;
}
async function devLogin() {
  const email = $("#dev-email").value.trim();
  try { ME = (await postJSON("/api/auth/dev", { email })).user; renderUser(); closeLogin(true); }
  catch (e) { $("#login-msg").textContent = e.message; }
}

/* api() dagi 401/403 javoblarini boshqaradi; true qaytsa so'rovni qayta yuborish kerak */
async function handleAuthFail(r) {
  let j = {}; try { j = await r.clone().json(); } catch (e) {}
  if (j.auth === "login") { ME = null; renderUser(); await askLogin("a_need"); return true; }
  if (j.auth === "blocked") throw new Error(L("a_blocked"));
  if (j.auth === "pending") throw new Error(L("a_pending"));
  return false;
}

/* ---------- ping (faollik) ---------- */
function startPing() {
  setInterval(() => { if (ME && !document.hidden) fetch("/api/ping", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {}); }, 60000);
}

/* ---------- admin panel ---------- */
function ago(ts) {
  if (!ts) return "—";
  const s = Math.floor(Date.now() / 1000) - ts;
  if (s < 120) return L("ad_now");
  if (s < 3600) return L("ad_ago_m", { n: Math.floor(s / 60) });
  if (s < 86400) return L("ad_ago_h", { n: Math.floor(s / 3600) });
  return L("ad_ago_d", { n: Math.floor(s / 86400) });
}
async function adminAct(email, action) {
  if (action === "delete" && !confirm(L("ad_confirm_del", { e: email }))) return;
  try { adminData = await postJSON("/api/admin/set", { email, action }); drawAdmin(); } catch (e) { toast(e.message); }
}
function drawAdmin() {
  const d = adminData; if (!d) return;
  const S = d.stats, me = ME ? ME.email : "";
  const stat = (k, v, cls) => h("div", { class: "ad-stat " + (cls || "") }, h("b", { text: String(v) }), h("span", { text: L(k) }));
  $("#ad-stats").replaceChildren(stat("ad_total", S.total), stat("ad_active", S.active, "live"), stat("ad_today", S.today),
    stat("ad_dl", S.downloads), stat("ad_pending", S.pending, S.pending ? "warnc" : ""), stat("ad_blocked", S.blocked));
  $("#ad-appr").checked = d.settings.require_approval;
  $("#ad-addbox").classList.toggle("hidden", !(ME && ME.role === "super"));
  const rows = d.users.map(u => {
    const btns = [];
    const isSuper = u.role === "super";
    if (!isSuper && !(u.role === "admin" && ME.role !== "super")) {
      if (!u.approved) btns.push(h("button", { class: "btn small", onclick: () => adminAct(u.email, "approve") }, L("ad_approve")));
      btns.push(h("button", { class: "btn small" + (u.blocked ? "" : " dangerous"), onclick: () => adminAct(u.email, u.blocked ? "unblock" : "block") }, L(u.blocked ? "ad_unblock" : "ad_block")));
      if (ME.role === "super") btns.push(h("button", { class: "btn small", onclick: () => adminAct(u.email, u.role === "admin" ? "remove_admin" : "make_admin") }, L(u.role === "admin" ? "ad_rmadm" : "ad_mkadm")));
      btns.push(h("button", { class: "btn small dangerous", onclick: () => adminAct(u.email, "delete") }, L("ad_del")));
    }
    const av = u.picture ? h("img", { class: "ava", src: u.picture, alt: "", referrerpolicy: "no-referrer", width: 32, height: 32 }) : h("span", { class: "ava ph" }, (u.name || u.email)[0].toUpperCase());
    return h("div", { class: "urow" + (u.blocked ? " blk" : "") },
      h("div", { class: "who" }, av, h("div", {}, h("b", { text: u.name || u.email }), h("small", { text: u.email + (u.email === me ? " ·" : "") }))),
      h("div", { class: "meta" },
        h("span", { class: "dot2" + (u.active ? " on" : "") }), h("span", { text: ago(u.last_seen) }),
        h("span", { class: "rolechip", text: L("r_" + u.role) }),
        !u.approved ? h("span", { class: "rolechip warn", text: L("ad_pending") }) : null,
        u.blocked ? h("span", { class: "rolechip bad", text: L("ad_blocked") }) : null,
        h("span", { class: "num", title: L("ad_logins"), text: "⇥ " + u.logins }), h("span", { class: "num", title: L("ad_dl"), text: "⬇ " + u.downloads })),
      h("div", { class: "acts" }, btns));
  });
  $("#ad-list").replaceChildren(...(rows.length ? rows : [h("p", { class: "hint", text: L("ad_empty") })]));
}
async function refreshAdmin() {
  try { adminData = await getJSON("/api/admin/users"); if (adminData.error) throw new Error(adminData.error); drawAdmin(); }
  catch (e) { toast(L("ad_forbidden")); location.hash = "#app"; }
}
let authReady = false;
function showAdmin(on) {
  clearInterval(adminTimer);
  if (!on || !authReady) return;
  if (!ME || !isAdmin()) {
    askLogin("a_need").then(() => { if (isAdmin()) showAdmin(true); else { toast(L("ad_forbidden")); location.hash = "#app"; } })
      .catch(() => { location.hash = "#app"; });
    return;
  }
  refreshAdmin(); adminTimer = setInterval(refreshAdmin, 15000);
}

function authLang() { renderUser(); if (adminData) drawAdmin(); }
async function authInit() {
  try { CFG = await getJSON("/api/config"); } catch (e) {}
  $("#login-close").addEventListener("click", () => closeLogin(false));
  $("#login").addEventListener("click", e => { if (e.target.id === "login") closeLogin(false); });
  $("#dev-go").addEventListener("click", devLogin);
  $("#ad-back").addEventListener("click", () => { location.hash = "#app"; });
  $("#ad-appr").addEventListener("change", async e => {
    try { adminData = await postJSON("/api/admin/settings", { require_approval: e.target.checked }); drawAdmin(); } catch (er) { toast(er.message); }
  });
  $("#ad-add").addEventListener("click", async () => {
    const v = $("#ad-email").value.trim(); if (!v) return;
    try { adminData = await postJSON("/api/admin/add_admin", { email: v }); $("#ad-email").value = ""; drawAdmin(); } catch (er) { toast(er.message); }
  });
  await loadMe(); authReady = true; startPing(); route();
}

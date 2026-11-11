"""Google orqali kirish, sessiyalar, foydalanuvchilar bazasi va admin amallari.

Baza: DATABASE_URL berilsa PostgreSQL (Neon/Supabase), aks holda SQLite fayl (faqat sinov uchun).
Obyektivka mazmuni bazaga yozilmaydi — faqat foydalanuvchi ma'lumoti va hisoblagichlar.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import urllib.parse
import urllib.request

SUPER = (os.environ.get("SUPER_ADMIN_EMAIL") or "").strip().lower()
CLIENT_ID = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
DEV = os.environ.get("DEV_LOGIN") == "1"            # faqat kompyuterda sinash uchun
DB_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.environ.get("USERS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.sqlite3"))
_SECRET = (os.environ.get("SESSION_SECRET") or secrets.token_hex(32)).encode()
SESSION_DAYS = 14
ACTIVE_SEC = 120
COOKIE = "andoza_sid"
_lock = threading.Lock()
_ready = False


class AuthError(Exception):
    def __init__(self, msg, code=401):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- baza
def _conn():
    if DB_URL:
        import psycopg  # requirements.txt da bor
        return psycopg.connect(DB_URL, autocommit=True), True
    c = sqlite3.connect(SQLITE_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c, False


def _q(sql: str, args=(), one=False, write=False):
    c, pg = _conn()
    try:
        if pg:
            sql = sql.replace("?", "%s")
        cur = c.cursor()
        cur.execute(sql, args)
        rows = None
        if not write:
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        if not pg:
            c.commit()
        return (rows[0] if rows else None) if one and rows is not None else rows
    finally:
        c.close()


def init_db():
    global _ready
    with _lock:
        if _ready:
            return
        _q("""CREATE TABLE IF NOT EXISTS users (
              email TEXT PRIMARY KEY, name TEXT, picture TEXT,
              role TEXT DEFAULT 'user', blocked INTEGER DEFAULT 0, approved INTEGER DEFAULT 1,
              created BIGINT, last_login BIGINT, last_seen BIGINT,
              logins INTEGER DEFAULT 0, downloads INTEGER DEFAULT 0)""", write=True)
        _q("CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT)", write=True)
        _ready = True


def get_setting(k, default="0"):
    init_db()
    r = _q("SELECT v FROM settings WHERE k=?", (k,), one=True)
    return r["v"] if r else default


def set_setting(k, v):
    init_db()
    if _q("SELECT k FROM settings WHERE k=?", (k,), one=True):
        _q("UPDATE settings SET v=? WHERE k=?", (str(v), k), write=True)
    else:
        _q("INSERT INTO settings (k, v) VALUES (?, ?)", (k, str(v)), write=True)


# ---------------------------------------------------------------- sessiya
def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_cookie(email: str, secure: bool) -> str:
    exp = int(time.time()) + SESSION_DAYS * 86400
    p = base64.urlsafe_b64encode(json.dumps({"e": email, "x": exp}).encode()).decode()
    val = f"{p}.{_sign(p)}"
    return (f"{COOKIE}={val}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}"
            + ("; Secure" if secure else ""))


def clear_cookie() -> str:
    return f"{COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def _email_from_cookie(header: str) -> str | None:
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE and "." in v:
            p, sig = v.rsplit(".", 1)
            if hmac.compare_digest(sig, _sign(p)):
                try:
                    d = json.loads(base64.urlsafe_b64decode(p.encode()))
                except Exception:
                    return None
                if d.get("x", 0) > time.time():
                    return d.get("e")
    return None


def _eff_role(u: dict) -> str:
    if u["email"] == SUPER and SUPER:
        return "super"
    return "admin" if u.get("role") == "admin" else "user"


def _public(u: dict) -> dict:
    return {"email": u["email"], "name": u.get("name") or "", "picture": u.get("picture") or "",
            "role": _eff_role(u), "approved": bool(u.get("approved")) or _eff_role(u) != "user",
            "blocked": bool(u.get("blocked"))}


def current_user(environ) -> dict | None:
    email = _email_from_cookie(environ.get("HTTP_COOKIE", ""))
    if not email:
        return None
    init_db()
    u = _q("SELECT * FROM users WHERE email=?", (email,), one=True)
    return u


def require_user(environ, need_ok=True) -> dict:
    u = current_user(environ)
    if not u:
        raise AuthError("login", 401)
    if need_ok:
        if u.get("blocked") and _eff_role(u) != "super":
            raise AuthError("blocked", 403)
        if not u.get("approved") and _eff_role(u) == "user":
            raise AuthError("pending", 403)
    return u


def optional_user(environ):
    """Yuklash uchun: kirgan bo'lsa tekshiradi; kirmagan bo'lsa — 'majburiy login' o'chiq bo'lsa mehmon sifatida o'tkazadi."""
    u = current_user(environ)
    if u:
        return require_user(environ)
    if get_setting("require_login") == "1":
        raise AuthError("login", 401)
    return None


def require_admin(environ) -> dict:
    u = require_user(environ, need_ok=False)
    if _eff_role(u) not in ("admin", "super"):
        raise AuthError("forbidden", 403)
    return u


def require_super(environ) -> dict:
    u = require_user(environ, need_ok=False)
    if _eff_role(u) != "super":
        raise AuthError("forbidden", 403)
    return u


# ---------------------------------------------------------------- kirish
def _verify_google(credential: str) -> dict:
    if not CLIENT_ID:
        raise AuthError("Google sozlanmagan (GOOGLE_CLIENT_ID)", 503)
    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"id_token": credential})
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read().decode())
    except Exception:
        raise AuthError("Google tokeni tasdiqlanmadi", 401)
    if d.get("aud") != CLIENT_ID or str(d.get("email_verified")) != "true" or not d.get("email"):
        raise AuthError("Google tokeni yaroqsiz", 401)
    if d.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise AuthError("Google tokeni yaroqsiz", 401)
    if int(d.get("exp", 0)) < time.time():
        raise AuthError("Google tokeni eskirgan", 401)
    return {"email": d["email"].lower(), "name": d.get("name", ""), "picture": d.get("picture", "")}


def _verify_access_token(token: str) -> dict:
    if not CLIENT_ID:
        raise AuthError("Google sozlanmagan (GOOGLE_CLIENT_ID)", 503)
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"access_token": token}), timeout=10) as r:
            ti = json.loads(r.read().decode())
        req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=10) as r:
            ui = json.loads(r.read().decode())
    except Exception:
        raise AuthError("Google tokeni tasdiqlanmadi", 401)
    if CLIENT_ID not in (ti.get("aud"), ti.get("azp")):
        raise AuthError("Google tokeni bu ilova uchun emas", 401)
    if not ui.get("email") or str(ui.get("email_verified")).lower() != "true":
        raise AuthError("Google email tasdiqlanmagan", 401)
    if ti.get("email") and ti["email"].lower() != ui["email"].lower():
        raise AuthError("Google tokeni yaroqsiz", 401)
    return {"email": ui["email"].lower(), "name": ui.get("name", ""), "picture": ui.get("picture", "")}


def login_google_token(token: str) -> dict:
    return _upsert(_verify_access_token(token))


def login_google(credential: str) -> dict:
    return _upsert(_verify_google(credential))


def login_dev(email: str, name: str = "") -> dict:
    if not DEV:
        raise AuthError("topilmadi", 404)
    return _upsert({"email": email.strip().lower(), "name": name or email.split("@")[0], "picture": ""})


def _upsert(info: dict) -> dict:
    init_db()
    now = int(time.time())
    u = _q("SELECT * FROM users WHERE email=?", (info["email"],), one=True)
    if u:
        _q("UPDATE users SET name=?, picture=?, last_login=?, last_seen=?, logins=logins+1 WHERE email=?",
           (info["name"], info["picture"], now, now, info["email"]), write=True)
    else:
        approved = 0 if get_setting("require_approval") == "1" and info["email"] != SUPER else 1
        role = "admin" if info["email"] == SUPER else "user"
        _q("INSERT INTO users (email,name,picture,role,blocked,approved,created,last_login,last_seen,logins,downloads)"
           " VALUES (?,?,?,?,0,?,?,?,?,1,0)",
           (info["email"], info["name"], info["picture"], role, approved, now, now, now), write=True)
    return _q("SELECT * FROM users WHERE email=?", (info["email"],), one=True)


def ping(u: dict):
    _q("UPDATE users SET last_seen=? WHERE email=?", (int(time.time()), u["email"]), write=True)


def count_download(u, n: int = 1):
    if u is None:
        set_setting("guest_downloads", int(get_setting("guest_downloads", "0")) + n)
        return
    _q("UPDATE users SET downloads=downloads+? WHERE email=?", (n, u["email"]), write=True)


# ---------------------------------------------------------------- admin
def list_users(actor: dict) -> dict:
    """Super admin hammani ko'radi; oddiy admin faqat oddiy foydalanuvchilarni (adminlarni emas)."""
    init_db()
    now = int(time.time())
    is_super = _eff_role(actor) == "super"
    rows = _q("SELECT * FROM users ORDER BY last_seen DESC")
    if not is_super:
        rows = [u for u in rows if _eff_role(u) == "user"]
    users = []
    for u in rows:
        p = _public(u)
        p.update({"created": u["created"], "last_login": u["last_login"], "last_seen": u["last_seen"],
                  "logins": u["logins"], "downloads": u["downloads"],
                  "active": bool(u["last_seen"] and now - u["last_seen"] <= ACTIVE_SEC)})
        users.append(p)
    return {"users": users,
            "stats": {"total": len(users), "active": sum(1 for x in users if x["active"]),
                      "today": sum(1 for x in users if x["last_login"] and now - x["last_login"] < 86400),
                      "downloads": sum(x["downloads"] or 0 for x in users),
                      "pending": sum(1 for x in users if not x["approved"]),
                      "blocked": sum(1 for x in users if x["blocked"]),
                      "guests": int(get_setting("guest_downloads", "0"))},
            "settings": {"require_approval": get_setting("require_approval") == "1",
                         "require_login": get_setting("require_login") == "1"},
            "viewer": "super" if is_super else "admin"}


def admin_action(actor: dict, email: str, action: str):
    email = (email or "").strip().lower()
    t = _q("SELECT * FROM users WHERE email=?", (email,), one=True)
    if not t:
        raise AuthError("Foydalanuvchi topilmadi", 404)
    actor_role, target_role = _eff_role(actor), _eff_role(t)
    if target_role == "super":
        raise AuthError("Super adminni o'zgartirib bo'lmaydi", 403)
    if action in ("make_admin", "remove_admin"):
        if actor_role != "super":
            raise AuthError("Faqat super admin adminlarni boshqaradi", 403)
        _q("UPDATE users SET role=? WHERE email=?", ("admin" if action == "make_admin" else "user", email), write=True)
        return
    if target_role == "admin" and actor_role != "super":
        raise AuthError("Adminni faqat super admin o'zgartira oladi", 403)
    if action == "delete" and actor_role != "super":
        raise AuthError("O'chirishni faqat super admin qiladi", 403)
    if action == "block":
        _q("UPDATE users SET blocked=1 WHERE email=?", (email,), write=True)
    elif action == "unblock":
        _q("UPDATE users SET blocked=0 WHERE email=?", (email,), write=True)
    elif action == "approve":
        _q("UPDATE users SET approved=1 WHERE email=?", (email,), write=True)
    elif action == "delete":
        _q("DELETE FROM users WHERE email=?", (email,), write=True)
    else:
        raise AuthError("Noma'lum amal", 400)


def add_admin_by_email(actor: dict, email: str):
    """Super admin hali kirmagan odamni ham admin qilib qo'yishi mumkin (u Google bilan kirganda admin bo'ladi)."""
    if _eff_role(actor) != "super":
        raise AuthError("Faqat super admin adminlarni boshqaradi", 403)
    email = (email or "").strip().lower()
    if "@" not in email:
        raise AuthError("Email noto'g'ri", 400)
    if not _q("SELECT email FROM users WHERE email=?", (email,), one=True):
        now = int(time.time())
        _q("INSERT INTO users (email,name,picture,role,blocked,approved,created,last_login,last_seen,logins,downloads)"
           " VALUES (?,?,?,?,0,1,?,0,0,0,0)", (email, "", "", "admin", now), write=True)
    else:
        _q("UPDATE users SET role='admin' WHERE email=?", (email,), write=True)

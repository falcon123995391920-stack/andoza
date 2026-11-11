"""Obyektivka sayti.

Ishga tushirish:   python server.py                  ->  http://127.0.0.1:8000
Tarmoq uchun:      python server.py --host 0.0.0.0   (OBJ_PASSWORD bilan!)
Parol (ixtiyoriy): OBJ_PASSWORD=maxfiy  (ixtiyoriy login: OBJ_USER=ism)
Boshqa serverda:   gunicorn server:application   yoki   waitress-serve server:application

Shaxsiy ma'lumotlar diskda saqlanmaydi: so'rov xotirada ishlanadi, vaqtinchalik fayllar o'chiriladi.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import io
import json
import mimetypes
mimetypes.add_type("application/manifest+json", ".webmanifest")
import os
import shutil
import sys
import tempfile
import traceback
import webbrowser
import zipfile
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import quote
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import builder  # noqa: E402
import auth  # noqa: E402
import core
import doclang  # noqa: E402
import obj_parser  # noqa: E402
import webconv as wc  # noqa: E402

MAX_BODY = 80 * 1024 * 1024
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
STATIC = BASE / "static"
SEC = [("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"),
       ("Referrer-Policy", "no-referrer"), ("Cache-Control", "no-store"),
       ("Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob: https://*.googleusercontent.com; "
        "style-src 'self' https://accounts.google.com/gsi/style; script-src 'self' https://accounts.google.com/gsi/client; "
        "connect-src 'self' https://accounts.google.com/gsi/; frame-src https://accounts.google.com/gsi/; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")]


class ApiError(Exception):
    def __init__(self, msg, code=400):
        super().__init__(msg)
        self.code = code


def _b64(data: str) -> bytes:
    if "," in data[:100]:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        raise ApiError("Fayl noto'g'ri yuborildi")


def _enc(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _photo_url(blob: bytes | None) -> str:
    """Rasmni ko'rsatish uchun kichraytirib data-URL qiladi."""
    if not blob:
        return ""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(blob)).convert("RGB")
        im.thumbnail((900, 1200))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=88)
        return "data:image/jpeg;base64," + _enc(out.getvalue())
    except Exception:
        return ""


def _read_input(d: dict):
    """text yoki fayl -> (xom person, rasm bayti)"""
    if d.get("text"):
        return obj_parser.parse_text(doclang.lat_to_cyr(str(d["text"]))), None
    if d.get("data"):
        name = str(d.get("filename", "fayl.docx"))
        ext = Path(name).suffix.lower()
        if ext not in (".docx", ".doc", ".txt"):
            raise ApiError("Faqat .docx, .doc yoki .txt fayl tanlang")
        tmp = tempfile.mkdtemp(prefix="obj_")
        try:
            path = Path(tmp) / ("in" + ext)
            path.write_bytes(_b64(d["data"]))
            return obj_parser.load_file(str(path))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    raise ApiError("Fayl yoki matn yuborilmadi")


def api_parse(d: dict):
    raw, photo = _read_input(d)
    std = _std(raw)
    web = wc.person_to_web(std)
    return {"person": web, "warnings": _warnings_with_targets(web, std, _lang(d)), "photo": _photo_url(photo)}


def _kept(rows):
    return [i for i, r in enumerate(rows or []) if str(r.get("text", "") or "").strip() or wc.period_compose(r)]


def _lang(d: dict) -> str:
    v = str(d.get("lang", "cy") or "cy")
    return v if v in doclang.LANGS else "cy"


def _std(raw: dict) -> dict:
    """Foydalanuvchi lotinda yozgan bo'lsa ham, ichki standart doim kirillda."""
    return core.standardize(doclang.to_cyrillic(raw))


def _warnings_with_targets(web: dict, std: dict, lang: str = "cy"):
    kw, kd = _kept(web.get("work")), _kept(web.get("deputy"))
    out = []
    for where, msg in core.check(std):
        tg = wc.locate(std, where, msg, kw, kd)
        w2, m2 = doclang.warn_text(where, msg, lang)
        item = {"where": w2, "msg": m2}
        if tg:
            item["target"] = tg
        out.append(item)
    return out


def api_check(d: dict):
    web = d.get("person") or {}
    std = _std(wc.web_to_person(web))
    return {"warnings": _warnings_with_targets(web, std, _lang(d))}


def _build_bytes(std: dict, photo_bytes: bytes | None, lang: str = "cy"):
    tmp = tempfile.mkdtemp(prefix="obj_")
    try:
        photo = None
        if photo_bytes:
            raw_img = Path(tmp) / "photo_in"
            raw_img.write_bytes(photo_bytes)
            try:
                photo = core.prepare_photo(str(raw_img), str(Path(tmp) / "photo.jpg"))
            except Exception:
                raise ApiError("Rasmni o'qib bo'lmadi (JPG yoki PNG tanlang)")
        out = Path(tmp) / "out.docx"
        builder.build(std, out, photo_path=photo, lang=lang)
        return out.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def api_build(d: dict):
    std = _std(wc.web_to_person(d.get("person") or {}))
    if not std.get("fio"):
        raise ApiError("Avval F.I.Sh. ni kiriting")
    blob = _build_bytes(std, _b64(d["photo"]) if d.get("photo") else None, _lang(d))
    return blob, builder.file_name(std["fio"]), len(core.check(std))


def api_convert(d: dict):
    """Ommaviy rejim: bitta faylni standartga keltiradi (rasmi saqlanadi)."""
    name = str(d.get("filename", "fayl"))
    if Path(name).suffix.lower() not in (".docx", ".doc"):
        raise ApiError("faqat .docx yoki .doc")
    raw, photo = _read_input(d)
    std = _std(raw)
    if not std.get("fio"):
        raise ApiError("Ф.И.Ш. топилмади — файл объективка эмасга ўхшайди")
    lang = _lang(d)
    blob = _build_bytes(std, photo, lang)
    return {"out": builder.file_name(std["fio"]), "docx": _enc(blob),
            "warnings": [{"where": a, "msg": b} for a, b in (doclang.warn_text(w, m, lang) for w, m in core.check(std))]}


def api_zip(d: dict):
    used, report = set(), []
    R = doclang.REPORT[_lang(d)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for it in d.get("items", []):
            src = str(it.get("name", "fayl"))
            if it.get("error"):
                report.append(f"{src}: {R['err']} — {it['error']}")
                continue
            base = Path(str(it["out"])).stem
            safe = "".join(c for c in base if c not in '\\/:*?"<>|') or "obyektivka"
            final, n = safe + ".docx", 2
            while final in used:
                final, n = f"{safe} ({n}).docx", n + 1
            used.add(final)
            z.writestr(final, _b64(it["docx"]))
            ws = it.get("warnings") or []
            report.append(f"{src} -> {final}: " + (R["ok"] if not ws else f"{len(ws)} {R['warns']}"))
            report += [f"    - {w['where']}: {w['msg']}" for w in ws]
        z.writestr("hisobot.txt", ("﻿" + "\n".join(report)).encode("utf8"))
    return buf.getvalue()


def api_relatives(d: dict):
    rels = core.standardize({"relatives": core.text_to_relatives(str(d.get("text", "")))})["relatives"]
    for r in rels:
        r["auto"] = True if r.get("auto") else r.get("auto", False)
    return {"relatives": [wc.rel_to_web(r) for r in rels]}


ROUTES_JSON = {"/api/relatives": api_relatives, "/api/parse": api_parse, "/api/check": api_check, "/api/convert": api_convert}


# -------------------------------------------------------------------- WSGI
def _auth_ok(environ) -> bool:
    pw = os.environ.get("OBJ_PASSWORD")
    if not pw:
        return True
    h = environ.get("HTTP_AUTHORIZATION", "")
    if not h.lower().startswith("basic "):
        return False
    try:
        user, given = base64.b64decode(h[6:]).decode("utf8").split(":", 1)
    except Exception:
        return False
    want_user = os.environ.get("OBJ_USER")
    ok_user = True if not want_user else hmac.compare_digest(user.encode(), want_user.encode())
    return hmac.compare_digest(given.encode(), pw.encode()) and ok_user


def _json(start, obj, code=200, extra=()):
    body = json.dumps(obj, ensure_ascii=False).encode("utf8")
    start(f"{code} {'OK' if code == 200 else 'Error'}",
          [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))] + list(extra) + SEC)
    return [body]


def _secure(environ) -> bool:
    return environ.get("HTTP_X_FORWARDED_PROTO", environ.get("wsgi.url_scheme", "")) == "https"


def _read_json(environ) -> dict:
    n = int(environ.get("CONTENT_LENGTH") or 0)
    if n > MAX_BODY:
        raise ApiError("Fayl juda katta", 413)
    return json.loads(environ["wsgi.input"].read(n) or b"{}")


def _auth_route(start, environ, method, path):
    """Kirish / admin yo'llari. Topilmasa None."""
    if method == "GET" and path == "/api/config":
        return _json(start, {"google_client_id": auth.CLIENT_ID, "dev": auth.DEV, "require_login": auth.get_setting("require_login") == "1"})
    if method == "GET" and path == "/api/me":
        u = auth.current_user(environ)
        return _json(start, {"user": auth._public(u) if u else None})
    if method == "GET" and path == "/api/admin/users":
        return _json(start, auth.list_users(auth.require_admin(environ)))
    if method != "POST" or not path.startswith(("/api/auth/", "/api/admin/", "/api/ping")):
        return None
    d = _read_json(environ)
    if path == "/api/auth/google":
        u = auth.login_google(str(d.get("credential", "")))
        return _json(start, {"user": auth._public(u)}, extra=[("Set-Cookie", auth.make_cookie(u["email"], _secure(environ)))])
    if path == "/api/auth/google_token":
        u = auth.login_google_token(str(d.get("access_token", "")))
        return _json(start, {"user": auth._public(u)}, extra=[("Set-Cookie", auth.make_cookie(u["email"], _secure(environ)))])
    if path == "/api/auth/dev":
        u = auth.login_dev(str(d.get("email", "")), str(d.get("name", "")))
        return _json(start, {"user": auth._public(u)}, extra=[("Set-Cookie", auth.make_cookie(u["email"], _secure(environ)))])
    if path == "/api/auth/logout":
        return _json(start, {"ok": True}, extra=[("Set-Cookie", auth.clear_cookie())])
    if path == "/api/ping":
        u = auth.require_user(environ, need_ok=False)
        auth.ping(u)
        return _json(start, {"ok": True})
    actor = auth.require_admin(environ)
    if path == "/api/admin/set":
        auth.admin_action(actor, str(d.get("email", "")), str(d.get("action", "")))
    elif path == "/api/admin/add_admin":
        auth.add_admin_by_email(actor, str(d.get("email", "")))
    elif path == "/api/admin/settings":
        auth.require_super(environ)
        for k in ("require_approval", "require_login"):
            if k in d:
                auth.set_setting(k, "1" if d.get(k) else "0")
    else:
        return None
    return _json(start, auth.list_users(actor))


def _static(start, rel: str):
    f = (STATIC / rel).resolve()
    if STATIC.resolve() not in f.parents or not f.is_file():
        return _json(start, {"error": "Topilmadi"}, 404)
    body = f.read_bytes()
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    start("200 OK", [("Content-Type", ctype), ("Content-Length", str(len(body)))] + SEC)
    return [body]


def application(environ, start_response):
    try:
        if not _auth_ok(environ):
            start_response("401 Unauthorized", [("WWW-Authenticate", 'Basic realm="Obyektivka"'),
                                                ("Content-Type", "text/plain; charset=utf-8")])
            return ["Parol kerak".encode()]
        method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/")
        r = _auth_route(start_response, environ, method, path)
        if r is not None:
            return r
        if method == "GET":
            if path in ("/", "/index.html"):
                return _static(start_response, "index.html")
            if path == "/health":
                return _json(start_response, {"ok": True})
            if path.startswith("/static/"):
                return _static(start_response, path[len("/static/"):])
            return _json(start_response, {"error": "Topilmadi"}, 404)
        if method == "POST" and (path in ROUTES_JSON or path in ("/api/build", "/api/zip")):
            data = _read_json(environ)
            user = auth.optional_user(environ) if path in ("/api/build", "/api/zip", "/api/convert") else None
            if path == "/api/build":
                blob, fname, nwarn = api_build(data)
                auth.count_download(user)
                start_response("200 OK", [
                    ("Content-Type", DOCX_MIME), ("Content-Length", str(len(blob))),
                    ("Content-Disposition", f"attachment; filename*=UTF-8''{quote(fname)}"),
                    ("X-Filename", quote(fname)), ("X-Warnings", str(nwarn)),
                    ("Access-Control-Expose-Headers", "X-Filename, X-Warnings")] + SEC)
                return [blob]
            if path == "/api/zip":
                blob = api_zip(data)
                auth.count_download(user, max(1, len(data.get("items") or [])))
                start_response("200 OK", [("Content-Type", "application/zip"),
                                          ("Content-Length", str(len(blob))),
                                          ("Content-Disposition", "attachment; filename=obyektivkalar.zip")] + SEC)
                return [blob]
            return _json(start_response, ROUTES_JSON[path](data))
        return _json(start_response, {"error": "Topilmadi"}, 404)
    except auth.AuthError as e:
        return _json(start_response, {"error": str(e), "auth": str(e) if str(e) in ("login", "blocked", "pending", "forbidden") else ""}, e.code)
    except ApiError as e:
        return _json(start_response, {"error": str(e)}, e.code)
    except json.JSONDecodeError:
        return _json(start_response, {"error": "So'rov noto'g'ri"}, 400)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        return _json(start_response, {"error": f"Ichki xatolik: {e.__class__.__name__}"}, 500)


class _Server(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, *a, **k):
        pass


def main():
    ap = argparse.ArgumentParser(description="Obyektivka sayti")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    srv = make_server(a.host, a.port, application, server_class=_Server, handler_class=_QuietHandler)
    url = f"http://{'127.0.0.1' if a.host in ('0.0.0.0', '') else a.host}:{a.port}"
    print(f"Sayt ishga tushdi: {url}   (to'xtatish: Ctrl+C)")
    if a.host not in ("127.0.0.1", "localhost") and not os.environ.get("OBJ_PASSWORD"):
        print("DIQQAT: sayt tarmoqqa ochiq, lekin parol qo'yilmagan (OBJ_PASSWORD).")
    if not a.no_browser and a.host in ("127.0.0.1", "localhost", "0.0.0.0"):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

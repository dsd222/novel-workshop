# -*- coding: utf-8 -*-
"""
本地「设定编辑器」—— 改世界书 / 角色卡，让 AI 改写，预览后写入
只监听 127.0.0.1，不对外。
"""
import os, sys, json, base64, shutil, difflib, urllib.request, urllib.error
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", 8321
ST_ROOT = os.environ.get("ST_ROOT") or os.path.join(os.path.expanduser("~"), "Desktop", "SillyTavern-release", "SillyTavern-release")
DATA = os.path.join(ST_ROOT, "data", "default-user")
WORLDS = os.path.join(DATA, "worlds")
CHARS = os.path.join(DATA, "characters")
BACKUP = os.path.join(DATA, "_设定备份")
HERE = os.path.dirname(os.path.abspath(__file__))

API_BASE = "https://api.deepseek.com/beta"
CARD_FIELDS = [
    ("description", "角色描述 / 主提示词"),
    ("scenario", "场景"),
    ("first_mes", "开局白"),
    ("mes_example", "对话示例"),
    ("post_history_instructions", "历史后指令（格式纪律）"),
    ("personality", "性格"),
]

# ---------------- 工具 ----------------
def read_json(p, default=None):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)

def backup(path):
    if not os.path.exists(path):
        return None
    os.makedirs(BACKUP, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BACKUP, f"{stem}.{ts}{ext}")
    shutil.copy2(path, dst)
    return dst

def get_secret(name="api_key_deepseek"):
    sec = read_json(os.path.join(DATA, "secrets.json"), {}) or {}
    vals = sec.get(name) or []
    if isinstance(vals, list):
        for v in vals:
            if isinstance(v, dict) and v.get("active") and v.get("value"):
                return v["value"].strip()
        if vals and isinstance(vals[0], dict):
            return (vals[0].get("value") or "").strip()
    return ""

def get_model():
    s = read_json(os.path.join(DATA, "settings.json"), {}) or {}
    return (s.get("oai_settings", {}) or {}).get("deepseek_model") or "deepseek-chat"

def png_text_read(path):
    from PIL import Image
    im = Image.open(path)
    return im, dict(im.text or {})

def png_card_load(path):
    im, txt = png_text_read(path)
    raw = txt.get("chara") or txt.get("ccv3")
    if not raw:
        return im, txt, None
    try:
        return im, txt, json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        return im, txt, None

def png_card_save(path, im, txt, card):
    from PIL.PngImagePlugin import PngInfo
    meta = PngInfo()
    for k, v in txt.items():
        if k in ("chara", "ccv3"):
            continue
        try:
            meta.add_text(k, v)
        except Exception:
            pass
    payload = base64.b64encode(json.dumps(card, ensure_ascii=False).encode("utf-8")).decode("ascii")
    meta.add_text("chara", payload)
    im.convert("RGB").save(path, "PNG", pnginfo=meta)

def make_diff(old, new):
    out = []
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                     lineterm="", n=2, fromfile="原文", tofile="改后"):
        esc = (line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        if line.startswith("+++") or line.startswith("---"):
            continue
        cls = "d-add" if line.startswith("+") else ("d-del" if line.startswith("-") else ("d-hunk" if line.startswith("@@") else ""))
        out.append(f'<span class="{cls}">{esc or "&nbsp;"}</span>')
    return "\n".join(out) if out else '<span class="d-hunk">（没有差异）</span>'

def call_chat(instruction, current, history):
    key = get_secret()
    if not key:
        raise RuntimeError("没找到 DeepSeek API Key（酒馆里可能还没保存成功）")
    system = (
        "你是一名中文文本编辑。用户给你一段原文和一条修改要求，你把原文改成要求的样子。\n"
        "你的输出会被直接写回文件，所以：只输出改好的正文本身。"
        "不要任何解释、标题、引号、代码块、「以下是」之类的开场白，也不要复述要求。\n"
        "保留原文格式：换行、【】标记、编号、全角空格缩进、人称和文风。\n"
        "这是一次多轮修改对话：每一轮用户都会重新给出「当前原文」，一律以那条为准；"
        "之前 assistant 的回复是你给出的旧版本，只作参考，不要把它们拼在一起。\n\n"
        "示例——\n"
        "要求：更短\n"
        "原文：他走得很慢，因为积雪已经没到膝盖，每一步都要把腿拔出来。\n"
        "输出：雪没到膝盖，他每走一步都得把腿拔出来。\n\n"
        "示例——\n"
        "要求：加一句关于气味\n"
        "原文：【冰下夹层】冰层与岩层之间的缝隙，天然避风。\n"
        "输出：【冰下夹层】冰层与岩层之间的缝隙，天然避风，但空气里有股铁锈混着霉的味道。"
    )
    msgs = [{"role": "system", "content": system}]
    for h in (history or [])[-8:]:
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({
        "role": "user",
        "content": f"这是当前原文：\n{current}\n\n要求：{instruction}",
    })
    body = {
        "model": get_model(),
        "messages": msgs,
        "temperature": 0.5,
        "max_tokens": 2048,
        "stream": False,
    }
    req = urllib.request.Request(
        API_BASE + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        raise RuntimeError(f"API {e.code}: {detail}")
    except Exception as e:
        raise RuntimeError(f"请求失败: {e}")
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError("返回格式异常: " + json.dumps(data, ensure_ascii=False)[:300])

# ---------------- 数据装配 ----------------
def list_worlds():
    out = []
    if not os.path.isdir(WORLDS):
        return out
    for fn in sorted(os.listdir(WORLDS)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(WORLDS, fn)
        j = read_json(p, {}) or {}
        ents = j.get("entries") or {}
        items = []
        for k, e in (ents.items() if isinstance(ents, dict) else enumerate(ents)):
            items.append({
                "id": str(k),
                "title": e.get("comment") or f"条目 {k}",
                "keys": e.get("key") or [],
                "content": e.get("content") or "",
                "constant": bool(e.get("constant")),
            })
        items.sort(key=lambda x: (0 if x["constant"] else 1, x["title"]))
        out.append({"file": fn, "name": j.get("name") or fn, "entries": items})
    return out

def list_cards():
    out = []
    if not os.path.isdir(CHARS):
        return out
    for fn in sorted(os.listdir(CHARS)):
        if not fn.lower().endswith(".png"):
            continue
        p = os.path.join(CHARS, fn)
        try:
            _, _, card = png_card_load(p)
        except Exception:
            continue
        if not card:
            continue
        d = card.get("data", card)
        items = [{"id": k, "title": label, "content": d.get(k) or ""} for k, label in CARD_FIELDS]
        for i, g in enumerate(d.get("alternate_greetings") or []):
            items.append({"id": f"alt:{i}", "title": f"备选开局 {i+1}", "content": g or ""})
        out.append({"file": fn, "name": d.get("name") or fn, "entries": items})
    return out

# ---------------- HTTP ----------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "r", encoding="utf-8") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self._send(200, {
                "worlds": list_worlds(), "cards": list_cards(),
                "st_root": ST_ROOT, "model": get_model(),
                "has_key": bool(get_secret()),
            })
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception as e:
            return self._send(400, {"error": f"bad request: {e}"})

        try:
            if self.path in ("/api/chat", "/api/ai"):
                txt = call_chat(req["instruction"], req["current"], req.get("history") or [])
                return self._send(200, {"text": txt, "diff": make_diff(req["current"], txt)})

            if self.path == "/api/save-world":
                p = os.path.join(WORLDS, req["file"])
                j = read_json(p)
                if j is None:
                    return self._send(404, {"error": "文件不存在"})
                ents = j.get("entries") or {}
                for item in req["entries"]:
                    k = item["id"]
                    e = ents.get(k) if isinstance(ents, dict) else None
                    if e is None:
                        continue
                    e["comment"] = item["title"]
                    e["key"] = item["keys"]
                    e["content"] = item["content"]
                    e["constant"] = bool(item["constant"])
                bak = backup(p)
                write_json(p, j)
                return self._send(200, {"ok": True, "backup": os.path.basename(bak or "")})

            if self.path == "/api/save-card":
                p = os.path.join(CHARS, req["file"])
                im, txt, card = png_card_load(p)
                if not card:
                    return self._send(400, {"error": "读取角色卡失败"})
                d = card.get("data", card)
                for item in req["entries"]:
                    i = item["id"]
                    if i.startswith("alt:"):
                        idx = int(i.split(":")[1])
                        d.setdefault("alternate_greetings", [])
                        d["alternate_greetings"][idx] = item["content"]
                    else:
                        d[i] = item["content"]
                bak = backup(p)
                png_card_save(p, im, txt, card)
                return self._send(200, {"ok": True, "backup": os.path.basename(bak or "")})

            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})

if __name__ == "__main__":
    print(f"ST_ROOT = {ST_ROOT}")
    print(f"worlds  = {len(list_worlds())}, cards = {len(list_cards())}, key = {bool(get_secret())}, model = {get_model()}")
    print(f"serving http://{HOST}:{PORT}/")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

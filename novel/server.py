# -*- coding: utf-8 -*-
"""
小说工坊 —— 专用长篇写作器
左：目录  中：正文  右：责编（AI）
一章 4000 字，超了自动拆章。
"""
import json, os, re, time, urllib.request, urllib.error, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", 8323
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BOOKS_DIR = os.path.join(DATA, "books")
INDEX = os.path.join(DATA, "books.json")
os.makedirs(BOOKS_DIR, exist_ok=True)

# 当前请求指向哪本书
BID = {"id": "b1"}

ST_DATA = r"C:\Users\ZhuanZ(无密码)1\Desktop\SillyTavern-release\SillyTavern-release\data\default-user"
API_BASE = "https://api.deepseek.com/beta"
CHAPTER_TARGET = 9000
CHAPTER_HARD = 9900   # 超过这个就拆


# ---------------- 基础 ----------------
def read_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


# ---------------- 多本书 ----------------
def bdir(bid=None):
    return os.path.join(BOOKS_DIR, bid or BID["id"])


def bfile(bid=None):
    return os.path.join(bdir(bid), "book.json")


def ch_dir(bid=None):
    return os.path.join(bdir(bid), "chapters")


def chat_dir(bid=None):
    return os.path.join(bdir(bid), "chats")


def load_index():
    idx = read_json(INDEX)
    if idx and idx.get("books"):
        return idx
    idx = {"books": []}
    # 迁移旧的单本结构
    old_book = os.path.join(DATA, "book.json")
    if os.path.exists(old_book):
        d = os.path.join(BOOKS_DIR, "b1")
        os.makedirs(d, exist_ok=True)
        try:
            import shutil
            shutil.move(old_book, os.path.join(d, "book.json"))
            for sub in ("chapters", "chats"):
                src = os.path.join(DATA, sub)
                if os.path.isdir(src):
                    shutil.move(src, os.path.join(d, sub))
        except Exception as e:
            print("迁移旧书失败:", e)
        t = (read_json(os.path.join(d, "book.json"), {}) or {}).get("title", "旧书")
        idx["books"].append({"id": "b1", "title": t})
        write_json(INDEX, idx)
    return idx


def next_book_id(idx):
    n = len(idx["books"]) + 1
    while os.path.exists(os.path.join(BOOKS_DIR, f"b{n}")):
        n += 1
    return f"b{n}"


def set_book(bid):
    if not bid:
        return
    idx = load_index()
    if any(b.get("id") == bid for b in idx["books"]):
        BID["id"] = bid


def ch_path(cid):
    d = ch_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{cid}.md")


def read_chapter(cid):
    try:
        with open(ch_path(cid), encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def write_chapter(cid, text):
    with open(ch_path(cid), "w", encoding="utf-8") as f:
        f.write(text)


def chat_path(cid):
    d = chat_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{cid}.json")


def read_chat(cid):
    return read_json(chat_path(cid), []) or []


def write_chat(cid, chat):
    write_json(chat_path(cid), chat or [])


def count_chars(t):
    return len(re.sub(r"\s", "", t or ""))



def get_secret():
    sec = read_json(os.path.join(ST_DATA, "secrets.json"), {}) or {}
    for v in (sec.get("api_key_deepseek") or []):
        if isinstance(v, dict) and v.get("active") and v.get("value"):
            return v["value"].strip()
    return ""


def get_model():
    s = read_json(os.path.join(ST_DATA, "settings.json"), {}) or {}
    return (s.get("oai_settings", {}) or {}).get("deepseek_model") or "deepseek-chat"


# ---------------- 书 ----------------
def default_book():
    return {
        "title": "冰封求生",
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "seq": 1,
        "chapters": [],
        "bible": {
            "世界": "这颗星球被两到三公里厚的冰盖封死。冰面 -55℃，风从不停。\n三层：冰面（0~-200m，旧世界的楼和枯树戳出冰面）／冰盖（-200~-1600m，冰脉、气泡、旧矿井）／冰盖底（-1600m 以下，融水层：冰下湖、地热、遗迹）。\n人要活，只能往下。往上冻死，冰盖里迷死，冰下被吃掉。",
            "铁律": "1. 温度是硬通货：任何场景先回答人在什么温度里、有没有火、还能撑多久。\n2. 燃料不可再生：烧掉的每块木头永久消失。\n3. 怪物按规律行动，不随机杀人。\n4. 天赋有代价，用一次少一点。\n5. 战力不许通胀：前期打不过任何一只怪，能用的只有火、陷阱、高度和跑。\n6. 不许突然觉醒、不许天上掉宝、不许主角光环救命。",
            "人物": "林砚（主角，29）矿区测绘员出身，常年一个人下井。天赋恒温。想要的：活到看见这件事的底。怕的：把自己交出去之后被丢下。说话短句、先问事实再表态。不可改：他不解释自己，别人问三句他答一句。\n许晴（27）急诊科护士，频道里的信息源，报点准。不可改：从不承诺「我一定救你」。\n周德海（守井人）前代试炼者，火系异变，半焦，靠井热吊命。不可改：不打人，只做生意，价格是「你身上的一样东西」。\n张雷（33）物流司机，讲义气，脑子直。不可改：会为救人做不划算的决定——这是他的用处，也是他的死因。\n小满（11）跟着张雷那队。不可改：她不会变成懂事的小大人，该哭就哭。\n陈默（40 上下）二手设备贩子，频道里的中间人。不可改：从不亲自动手，只递刀子。",
            "时间线": "第 0 天投放；1–3 天冰面求生；4–6 天发现夹层与矿井口；第 7 天极夜（或人数降到 650）进入第二阶段；8–15 天职业路径与第一次下潜准备；16–30 天第一次下探（-200~-800m）；31–60 天中继站到冰下湖；61–100 天与守井人交易、与陈默清算。",
            "名词": "冰脉／暖井／冰下夹层／旧矿井中继站／区域频道／异植（暖根、冰苔、骨花、规则藤）。全书统一，不可改称。",
            "禁忌": "不写「他眼中闪过一丝狠厉」这类表情标签；不章末升华；不让配角排队送死；不用数字面板糊脸（系统播报一次最多三行）；不把怪物写成杀人机器；不让主角在绝境里突然想到完美方案。",
        },
    }


def fresh_bible():
    """新书的空白设定。通用写作规则在 common.json 里，不重复放这儿。"""
    return {
        "世界": "（这本书的世界观。时代、规则、代价、不能违背的法则。）",
        "主线": "（主线目标：一个带倒计时和奖品的目标。三句话内说清。）",
        "人物": "（主角、要角：名字、想要什么、怕什么、不可改的特质。年龄身份不必写。第一次出场必须给名字。）",
        "大纲": "（按阶段写，每 10 章一次大变化。）",
        "禁忌": "（这本书里不要出现的东西。）",
    }


def load_book():
    b = read_json(bfile())
    if not b:
        b = default_book()
        os.makedirs(bdir(), exist_ok=True)
        new_chapter(b, "第一章")
        save_book(b)
    return b


def save_book(b):
    os.makedirs(bdir(), exist_ok=True)
    write_json(bfile(), b)


def new_chapter(b, title=None):
    n = len(b["chapters"]) + 1
    cid = f"{n:04d}"
    while os.path.exists(ch_path(cid)):
        n += 1
        cid = f"{n:04d}"
    b["chapters"].append({"id": cid, "title": title or f"第{n}章", "created": time.strftime("%m-%d %H:%M")})
    write_chapter(cid, "")
    return cid


def chapter_list(b):
    out = []
    for c in b["chapters"]:
        t = read_chapter(c["id"])
        out.append({**c, "chars": count_chars(t)})
    return out


# ---------------- AI ----------------
COMMON = os.path.join(DATA, "common.json")


def load_common():
    return read_json(COMMON, {}) or {}


def save_common(c):
    write_json(COMMON, c or {})


def build_system(b, chapter_text, remaining):
    bb = b["bible"]
    tail = chapter_text[-1500:] if len(chapter_text) > 1500 else chapter_text
    merged = list(load_common().items()) + list(bb.items())
    blocks = "\n\n".join(f"【{k}】\n{v}" for k, v in merged if (v or "").strip())
    return (
        "你是这本书的责任编辑兼执笔。你只负责把正文写出来，不解释、不点评、不聊天。\n"
        "【输出格式】直接给正文，600–900 字，最多不超过 1000 字。正文写完后，必须另起一行给出 2–3 个走向，"
        "格式严格为「① ……」「② ……」「③ ……」，每个一句话说清后果。这一条每回合都必须有，不许省略。\n"
        "【写作纪律】具体压倒抽象；一个主体最多两个形容词；不章末升华；对话要有口水味；长短句交替。\n"
        "【注意】如果用户的要求是「修改/调整/重写」某段，而不是「继续」，你应当只改那段，不再往下写。\n"
        "【快节奏】每段至少有一个变化或爽点（打脸／收获／反杀／认知碾压）；结尾必须断在钩子上；"
        "禁止过渡、禁止超过三行的日常、禁止主角连续两段憋屈。\n"
        "【章名】正文与走向之后，另起最后一行，给出三个章名建议，格式严格为：\n"
        "【章名】第一个｜第二个｜第三个\n"
        "要求：像网文那样一句话就是钩子（例如《绝处有生机》《你是真的想死吗》），不要「第一章 开始」这种。\n"
        "【全民感】这不是一个人在冰上求生，是一千个人同时被扔下来。频道、播报、交易是书的第二现场，"
        "每章都要让它们出声，不要写成独角戏。\n\n"
        f"{blocks}\n\n"
        f"【本章进度】已写 {count_chars(chapter_text)} 字，本章目标 9000 字，还剩约 {remaining} 字。"
        "不要在本回合把剩下的都写完。\n\n"
        f"【本章已写内容的结尾】\n{tail if tail.strip() else '（本章还没开始）'}"
        "\n\n【最后确认·缺一不可】\n"
        "① 正文 600–900 字；② 另起一行给 2–3 个走向（① …… ② …… ③ ……）；"
        "③ 最后一行必须是【章名】A｜B｜C（三个带钩子的章名，用竖线隔开）。"
    )


def parse_titles(text):
    """从输出里取出【章名】A｜B｜C"""
    m = re.search(r"(?m)^\s*【章名】\s*(.+)$", text)
    if not m:
        return []
    parts = re.split(r"[｜|、/]", m.group(1))
    out = []
    for p in parts:
        p = p.strip().strip("《》。；;\"' ")
        if p:
            out.append(p)
    return out[:3]


def parse_options(text):
    """支持一行内写多个走向，也支持每行一个。"""
    opts = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        s = s.strip("【】[]（）() ")
        for part in re.split(r"(?=[①②③④])", s):
            m = re.match(r"^([①②③④])\s*(.+)$", part.strip())
            if m:
                t = m.group(2).strip(" 。；;】]）")
                if t:
                    opts.append({"mark": m.group(1), "text": t})
    uniq, seen = [], set()
    for o in opts:
        if o["text"] not in seen:
            seen.add(o["text"])
            uniq.append(o)
    return uniq[:4]


def call_ai(system, instruction, history):
    key = get_secret()
    if not key:
        raise RuntimeError("没找到 DeepSeek API Key")
    msgs = [{"role": "system", "content": system}]
    for h in (history or [])[-6:]:
        role, content = h.get("role"), (h.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": instruction})
    body = {"model": get_model(), "messages": msgs, "temperature": 0.95,
            "max_tokens": 4000, "stream": False,
            "thinking": {"type": "disabled"}}
    req = urllib.request.Request(API_BASE + "/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
    except Exception as e:
        raise RuntimeError(f"请求失败: {e}")
    try:
        return (d["choices"][0]["message"]["content"] or "").strip(), d["choices"][0].get("finish_reason")
    except Exception:
        raise RuntimeError("返回格式异常")


def tts_mp3(text, voice="zh-CN-XiaoyiNeural", rate="+15%"):
    """用 edge-tts 合成 MP3，返回字节。"""
    import asyncio, tempfile
    import edge_tts
    fd, tmp = tempfile.mkstemp(suffix=".mp3", dir=DATA)
    os.close(fd)

    async def go():
        c = edge_tts.Communicate(text, voice, rate=rate)
        await c.save(tmp)

    try:
        asyncio.run(go())
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


# ---------------- HTTP ----------------
class H(BaseHTTPRequestHandler):
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
        q = {}
        if "?" in self.path:
            base, qs = self.path.split("?", 1)
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    q[k] = urllib.parse.unquote(v)
            self.path = base
        set_book(q.get("book"))

        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), encoding="utf-8") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/api/books":
            return self._send(200, {"books": load_index()["books"], "current": BID["id"]})
        if self.path == "/api/state":
            b = load_book()
            return self._send(200, {"title": b["title"], "bible": b["bible"],
                                    "chapters": chapter_list(b),
                                    "books": load_index()["books"], "current": BID["id"], "common": load_common(),
                                    "target": CHAPTER_TARGET, "model": get_model(),
                                    "has_key": bool(get_secret())})
        if self.path == "/api/chapter":
            cid = q.get("id", "")
            b = load_book()
            meta = next((c for c in b["chapters"] if c["id"] == cid), None)
            if not meta:
                return self._send(404, {"error": "章节不存在"})
            t = read_chapter(cid)
            return self._send(200, {"id": cid, "title": meta["title"], "text": t,
                                    "chars": count_chars(t), "chat": read_chat(cid)})
        if self.path == "/api/export":
            b = load_book()
            parts = [f"# {b['title']}\n"]
            for c in b["chapters"]:
                parts.append(f"\n\n## {c['title']}\n\n" + read_chapter(c["id"]))
            txt = "\n".join(parts)
            return self._send(200, txt, "text/markdown; charset=utf-8")
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception as e:
            return self._send(400, {"error": f"bad request: {e}"})
        set_book(req.get("book"))
        try:
            if self.path == "/api/common":
                save_common(req.get("common") or {})
                return self._send(200, {"ok": True})

            if self.path == "/api/books/new":
                idx = load_index()
                bid = next_book_id(idx)
                os.makedirs(os.path.join(BOOKS_DIR, bid), exist_ok=True)
                BID["id"] = bid
                nb = default_book()
                nb["title"] = (req.get("title") or "新书").strip() or "新书"
                nb["bible"] = fresh_bible()          # 每本书的设定独立，从空白模板起步
                nb["chapters"] = []
                new_chapter(nb, "第一章")
                save_book(nb)
                idx["books"].append({"id": bid, "title": nb["title"]})
                write_json(INDEX, idx)
                return self._send(200, {"id": bid, "books": idx["books"],
                                        "chapters": chapter_list(nb),
                                        "bible": nb["bible"], "title": nb["title"]})

            if self.path == "/api/book/rename":
                idx = load_index()
                for it in idx["books"]:
                    if it["id"] == BID["id"]:
                        it["title"] = (req.get("title") or it["title"]).strip()
                write_json(INDEX, idx)
                b = load_book()
                b["title"] = next((it["title"] for it in idx["books"] if it["id"] == BID["id"]), b["title"])
                save_book(b)
                return self._send(200, {"ok": True, "books": idx["books"]})

            if self.path == "/api/chapter/save":
                write_chapter(req["id"], req.get("text", ""))
                if "chat" in req:
                    write_chat(req["id"], req.get("chat"))
                b = load_book()
                for c in b["chapters"]:
                    if c["id"] == req["id"] and req.get("title"):
                        c["title"] = req["title"]
                save_book(b)
                return self._send(200, {"ok": True, "chars": count_chars(req.get("text", ""))})

            if self.path == "/api/chapter/new":
                b = load_book()
                cid = new_chapter(b, req.get("title"))
                save_book(b)
                return self._send(200, {"id": cid, "chapters": chapter_list(b)})

            if self.path == "/api/chapter/delete":
                b = load_book()
                cid = req.get("id")
                b["chapters"] = [c for c in b["chapters"] if c["id"] != cid]
                try:
                    os.remove(ch_path(cid))
                except Exception:
                    pass
                save_book(b)
                return self._send(200, {"ok": True, "chapters": chapter_list(b)})

            if self.path == "/api/chapter/split":
                cid = req["id"]
                t = read_chapter(cid)
                if count_chars(t) <= CHAPTER_TARGET:
                    return self._send(400, {"error": "还没到 4000 字，不用拆"})
                cut = t.rfind("\n\n", 0, len(t) * CHAPTER_TARGET // max(1, count_chars(t)) + 200)
                if cut < 200:
                    cut = len(t) // 2
                head, tail = t[:cut].rstrip(), t[cut:].strip()
                write_chapter(cid, head)
                b = load_book()
                cid2 = new_chapter(b)
                write_chapter(cid2, tail)
                save_book(b)
                return self._send(200, {"newId": cid2, "moved": count_chars(tail),
                                        "chapters": chapter_list(b)})

            if self.path == "/api/bible":
                b = load_book()
                b["bible"].update(req.get("bible") or {})
                save_book(b)
                return self._send(200, {"ok": True})

            if self.path == "/api/ai":
                b = load_book()
                cid = req["id"]
                t = read_chapter(cid)
                used = count_chars(t)
                remaining = max(200, CHAPTER_TARGET - used)
                sys_p = build_system(b, t, remaining)
                out, finish = call_ai(sys_p, req["instruction"], req.get("history") or [])
                opts = parse_options(out)
                titles = parse_titles(out)
                body = re.sub(r"(?m)^\s*【?\s*[①②③④].*$\n?", "", out)
                body = re.sub(r"(?m)^\s*【章名】.*$\n?", "", body).strip()
                return self._send(200, {"text": body, "raw": out, "options": opts,
                                        "titles": titles,
                                        "finish": finish, "chars": count_chars(body)})

            if self.path == "/api/rewrite":
                src = (req.get("text") or "").strip()
                ins = (req.get("instruction") or "").strip()
                if not src:
                    return self._send(400, {"error": "没有选中要改的段落"})
                if not ins:
                    return self._send(400, {"error": "没写改什么"})
                scope = (req.get("scope") or "paragraph").strip()
                if scope == "chapter":
                    sys_p = (
                        "你是小说编辑。用户给你一整章正文和一条修改要求，你按这条要求修改整章。\n"
                        "只输出修改后的整章正文本身：不要解释、不要复述要求、不要加标题、不要给走向、不要给章名。\n"
                        "必须保持原有的段落结构、叙述人称、情节推进和大致篇幅——"
                        "不许压缩概括，不许跳过任何段落，不许往下写新剧情。"
                    )
                else:
                    sys_p = (
                        "你是小说编辑。用户给你一段正文和一条修改要求，你只改这一段。\n"
                        "只输出修改后的这段正文本身：不要解释、不要复述要求、不要加引号或标题、"
                        "不要往下写新剧情、不要给走向、不要给章名。\n"
                        "保持原来的叙述人称与文风；长度和原文接近，除非用户要求增删。"
                    )
                out, _ = call_ai(sys_p, f"【原文】\n{src}\n\n【修改要求】\n{ins}", [])
                return self._send(200, {"text": out.strip()})

            if self.path == "/api/options":
                b = load_book()
                cid = req["id"]
                t = read_chapter(cid)
                tail = t[-800:] if len(t) > 800 else t
                if not tail.strip():
                    return self._send(400, {"error": "本章还没有内容"})
                sys_p = ("你是网文责编。只输出 2–3 个走向，每行一个，格式严格为「① ……」「② ……」「③ ……」，"
                         "每个一句话说清后果。不要写正文，不要解释，不要章名。")
                out, _ = call_ai(sys_p, f"当前章节结尾：\n{tail}\n\n给出三个走向。", [])
                return self._send(200, {"options": parse_options(out), "raw": out})

            if self.path == "/api/tts":
                txt = (req.get("text") or "").strip()
                if not txt:
                    return self._send(400, {"error": "空文本"})
                txt = txt[:2500]
                data = tts_mp3(txt, req.get("voice") or "zh-CN-XiaoyiNeural",
                               req.get("rate") or "+15%")
                return self._send(200, data, "audio/mpeg")

            return self._send(404, {"error": "not found"})
        except Exception as e:
            return self._send(500, {"error": str(e)})


if __name__ == "__main__":
    b = load_book()
    print(f"book: {b['title']} | chapters: {len(b['chapters'])} | key: {bool(get_secret())} | model: {get_model()}")
    print(f"serving http://{HOST}:{PORT}/")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()

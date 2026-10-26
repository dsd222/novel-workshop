# -*- coding: utf-8 -*-
"""给《神秘复苏》加「独立个体」线：新增一条世界书 + 新增开局 + 描述补丁"""
import json, base64, os, shutil, time
from PIL import Image
from PIL.PngImagePlugin import PngInfo

DATA = r"C:\Users\ZhuanZ(无密码)1\Desktop\SillyTavern-release\SillyTavern-release\data\default-user"
WORLD = os.path.join(DATA, "worlds", "神秘复苏-世界书.json")
CARD = os.path.join(DATA, "characters", "神秘复苏-主持人.png")
BAK = os.path.join(DATA, "_设定备份")
os.makedirs(BAK, exist_ok=True)
ts = time.strftime("%Y%m%d-%H%M%S")

# ---------------- 1. 世界书：加 20 独立线 ----------------
NEW_ENTRY = {
    "uid": 20,
    "key": ["独立", "原著", "杨间", "主线"],
    "keysecondary": [],
    "comment": "20 独立线（默认生效）",
    "content": (
        "【独立线·优先级最高】\n"
        "{{user}}不在这本书的主线里。杨间、张伟、周正、方镜、王珊珊这些人活在这个世界上，"
        "但他们在几百公里外的另一座城市，走他们自己的故事。\n"
        "除非{{user}}主动去找他们，否则不要让他们出现、不要让他们“恰好路过”、不要用他们推动剧情。\n"
        "这本书写的是{{user}}——一个和原著无关的人，在这个正在复苏的世界里怎么活。\n"
        "原著只提供三样东西：世界规则、鬼的运作方式、以及这个时代的气氛。剧情由你现场生成。"
    ),
    "constant": True,
    "vectorized": False,
    "selective": True,
    "selectiveLogic": 0,
    "addMemo": True,
    "order": 5,
    "position": 0,
    "disable": False,
    "excludeRecursion": False,
    "preventRecursion": False,
    "delayUntilRecursion": False,
    "probability": 100,
    "useProbability": True,
    "depth": 4,
    "group": "",
    "groupOverride": False,
    "groupWeight": 100,
    "scanDepth": None,
    "caseSensitive": None,
    "matchWholeWords": None,
    "useGroupScoring": None,
    "automationId": "",
    "role": 0,
    "sticky": 0,
    "cooldown": 0,
    "delay": 0,
    "matchPersonaDescription": False,
    "matchCharacterDescription": False,
    "matchCharacterPersonality": False,
    "matchCharacterDepthPrompt": False,
    "matchScenario": False,
    "matchCreatorNotes": False,
    "triggers": [],
    "extensions": {},
}

shutil.copy2(WORLD, os.path.join(BAK, f"神秘复苏-世界书.{ts}.json"))
w = json.load(open(WORLD, encoding="utf-8"))
w["entries"]["20"] = NEW_ENTRY
tmp = WORLD + ".tmp"
json.dump(w, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.replace(tmp, WORLD)
print("世界书: 现有", len(w["entries"]), "条，已加入 20 独立线")

# ---------------- 2. 角色卡：加开局 + 描述补丁 ----------------
GREETING = """　　你醒过来的时候，手心里攥着一张湿透的纸。

　　不是你家。是一间老式出租屋，墙皮鼓着泡，霉味很重。窗外是一座陌生的小县城，路灯亮着，街上一个人也没有。

　　电视开着，静音。屏幕下方滚着一行字：

　　　　「……本市第三人民医院今日凌晨发生不明原因死亡事件，已封锁，请市民绕行……」

　　手机在床头震动。屏幕上是一个群，47 人，群名：南城灵异观察。

　　最新一条，两分钟前：

　　　　「有人在三院后门看到东西了。别去。」

　　下面跟着一张照片，拍得很糊。夜里的走廊，尽头站着一个人形。它是站着的，但脖子折成了一个不正常的角度。

　　你低头看了眼自己的手。手背很干净。

　　但你记得——昨天夜里，你在三院那栋楼里，见过那东西。

　　你也记得，你活着出来了。这不太对。

　　——请选择你的行动：
　　①【谨慎】先把那张湿纸摊开看清楚，再翻手机的通话记录——确认自己昨天到底是怎么回来的。
　　②【冒险】出门，去三院。趁天还没亮，趁那东西还在。
　　③【情感】在群里回一条：「我昨晚在三院。你们谁也在？」

　　或者，写下你自己想做的事。

　　[ 第1天 · 05:40 ｜ 南城·老城区出租屋 ｜ 状态：手抖，想不起来昨晚 ｜ 复苏度：— ]"""

DESC_BLOCK = """【关于原著人物】
杨间、张伟、周正、方镜、王珊珊这些人活在这个世界上，但他们在另一座城市，走他们自己的线。
除非{{user}}主动去找，否则不要让他们出现、不要让他们「恰好路过」、不要用他们推动剧情。
这本书写的是{{user}}——一个和原著无关的人。原著只提供世界规则、鬼的运作方式和时代气氛，剧情由你现场生成。
{{user}}的身份、能力、来历由玩家自己定；玩家没说的，你也不许替他编。

"""

shutil.copy2(CARD, os.path.join(BAK, f"神秘复苏-主持人.{ts}.png"))
im = Image.open(CARD)
txt = dict(im.text or {})
card = json.loads(base64.b64decode(txt["chara"]).decode("utf-8"))
d = card["data"]

desc = d.get("description") or ""
if "【关于原著人物】" not in desc:
    if "【每回合固定结构】" in desc:
        desc = desc.replace("【每回合固定结构】", DESC_BLOCK + "【每回合固定结构】", 1)
    else:
        desc = desc + "\n\n" + DESC_BLOCK
    d["description"] = desc
    print("角色卡: 描述已补丁")
else:
    print("角色卡: 描述已有该段，跳过")

alts = d.setdefault("alternate_greetings", [])
if GREETING not in alts:
    alts.append(GREETING)
    print("角色卡: 开局数 ->", len(alts) + 1)
else:
    print("角色卡: 开局已存在")

meta = PngInfo()
for k, v in txt.items():
    if k in ("chara", "ccv3"):
        continue
    try:
        meta.add_text(k, v)
    except Exception:
        pass
meta.add_text("chara", base64.b64encode(json.dumps(card, ensure_ascii=False).encode("utf-8")).decode("ascii"))
im.convert("RGB").save(CARD, "PNG", pnginfo=meta)

chk = json.loads(base64.b64decode(Image.open(CARD).text["chara"]).decode("utf-8"))["data"]
print("校验: 开局", len(chk["alternate_greetings"]) + 1, "条 | 描述", len(chk["description"]), "字")

# -*- coding: utf-8 -*-
"""关闭《神秘复苏》世界书里剩下 3 条纯原著人名/地名条目（鬼的条目全部保留）"""
import json, os, shutil, time

DATA = r"C:\Users\ZhuanZ(无密码)1\Desktop\SillyTavern-release\SillyTavern-release\data\default-user"
WORLD = os.path.join(DATA, "worlds", "神秘复苏-世界书.json")
BAK = os.path.join(DATA, "_设定备份")
os.makedirs(BAK, exist_ok=True)

TARGETS = ["13 大昌市", "17 张羡光", "19 曹延华"]

shutil.copy2(WORLD, os.path.join(BAK, f"神秘复苏-世界书.{time.strftime('%Y%m%d-%H%M%S')}.json"))
w = json.load(open(WORLD, encoding="utf-8"))
e = w["entries"]

hit = [v["comment"] for k, v in e.items() if v.get("comment") in TARGETS]
for k, v in e.items():
    if v.get("comment") in TARGETS:
        v["disable"] = True

tmp = WORLD + ".tmp"
json.dump(w, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.replace(tmp, WORLD)

print("已关闭:", ", ".join(hit))
print()
print("最终状态:")
for k in sorted(e, key=lambda x: int(x)):
    v = e[k]
    flags = []
    if v.get("constant"): flags.append("常驻")
    flags.append("已关" if v.get("disable") else "启用")
    print(f"  {v['comment']:<22} {' / '.join(flags)}")

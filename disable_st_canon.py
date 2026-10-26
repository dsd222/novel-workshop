# -*- coding: utf-8 -*-
"""关闭《神秘复苏》世界书里的 5 条原著人物条目"""
import json, os, shutil, time

DATA = r"C:\Users\ZhuanZ(无密码)1\Desktop\SillyTavern-release\SillyTavern-release\data\default-user"
WORLD = os.path.join(DATA, "worlds", "神秘复苏-世界书.json")
BAK = os.path.join(DATA, "_设定备份")
os.makedirs(BAK, exist_ok=True)

TARGETS = ["02 杨间", "03 周正", "04 张伟", "05 王珊珊", "06 方镜"]

shutil.copy2(WORLD, os.path.join(BAK, f"神秘复苏-世界书.{time.strftime('%Y%m%d-%H%M%S')}.json"))
w = json.load(open(WORLD, encoding="utf-8"))
e = w["entries"]

hit = []
for k, v in e.items():
    if v.get("comment") in TARGETS:
        v["disable"] = True
        hit.append(v["comment"])

tmp = WORLD + ".tmp"
json.dump(w, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.replace(tmp, WORLD)

print("已关闭:", ", ".join(hit))
print()
print("当前状态:")
for k in sorted(e, key=lambda x: int(x)):
    v = e[k]
    flags = []
    if v.get("constant"): flags.append("常驻")
    if v.get("disable"): flags.append("已关")
    print(f"  {v['comment']:<22} {' / '.join(flags) if flags else '启用'}")

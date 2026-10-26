# 小说工坊 / novel-workshop

一套自用的小说写作 + 角色扮演工具链。核心是一本正在写的长篇：**《冰封求生》**（全民冰封求生题材）。

## 包含什么

### 1. `novel/` —— 小说工坊（写作器）

三栏界面：左目录 / 中正文 / 右 AI 责编。

- `server.py`：Python 标准库起服务，端口 **8323**，无第三方依赖
- `index.html`：单文件前端
- `data/`：书稿与设定
  - `common.json`：**通用写作规则**（节奏 / 笔法 / 角色介绍法），所有书共享
  - `books/<id>/book.json`：每本书独立的设定库（世界观、主线、人物、规则、怪物、力量体系……）
  - `books/<id>/chapters/*.md`：正文，一章一个文件
  - `books/<id>/chats/*.json`：与 AI 的对话与「走向」选项

**功能**

- 每章目标字数可调（当前 9000），满了可一键拆章
- AI 续写：每段 600–900 字，必定给 2–3 个走向 + 3 个章名建议
- 「改这段」/「改整章」：独立改写通道，只改不续写，可撤销
- Edge TTS 朗读（走 `edge-tts` Python 包）
- 多本书切换，设定随书独立
- 导出整本 Markdown

**跑起来**

```bash
python server.py
# 打开 http://127.0.0.1:8323/
```

Windows 可以用 `novel/启动小说工坊.bat`（检测端口 → 后台起服务 → 开浏览器）。

DeepSeek 的 API Key 从 SillyTavern 的 `data/default-user/secrets.json` 读取，**不存本仓库**。

### 2. `editor/` —— 设定编辑器（端口 8321）

三栏的设定库编辑器，带 AI 改写侧栏。同样是 `python server.py`。

### 3. `ext/story-rewriter/` —— SillyTavern 扩展「剧情改写」

装在 `SillyTavern/data/default-user/extensions/` 下，在酒馆里就地改写最后一条 AI 回复，支持撤销。

### 4. `out/` —— 生成物

角色卡（PNG，含内嵌 V2 卡片数据）、世界书 JSON。

### 5. 根目录脚本

`gen_*.py` 是生成角色卡/世界书的脚本（Pillow 生成 PNG + 写入 `chara` tEXt 块），`patch_st_*.py` / `disable_st_canon*.py` 是改酒馆配置的一次性脚本。

## 《冰封求生》设定概要

- 十万人被投放，分八个区，北七区一千人，面积约一万五千平方公里
- 每十天一轮寒潮：−55℃ 一路降到 −130℃，人只能一层层往下退
- 天赋人人有，但大多很小、很具体、有代价
- 庇护所登记制：连续待六小时才算数，寿命 72 小时就塌，得一直搬家
- 主角：21 岁土木系大三，**看冰很清楚，看人很糊涂**
- 系统开三张榜（深度/击杀/存活），排名是唯一的进度条

## 注意

- 仓库是**私有**的
- 不含任何密钥
- 写完记得 `git pull` 同步（本机未装 git，目前靠 API 上传）

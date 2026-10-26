/**
 * 剧情改写 —— 在聊天页右侧加一个小窗口
 * 用当前模型的 API 改写最后一条（或指定一条）AI 回复，确认后原地替换。
 */
import { chat, generateQuietPrompt, saveChatConditional, reloadCurrentChat } from '../../../../script.js';

const SYS = [
    '你是一名中文小说的文字编辑。',
    '用户会给你一段小说正文和一条修改要求，你把正文改成要求的样子。',
    '只输出改写后的正文本身：不要解释、不要复述要求、不要加引号或代码块、不要加「改写后」这种标签。',
    '保留原有格式：换行、全角空格缩进、第二人称、文风，以及结尾的①②③选项和状态栏。',
].join('\n');

const $q = (s) => document.querySelector(s);

let st = { idx: -1, old: '', text: '' };
let lastUndo = null;
let busy = false;

function setStatus(msg) {
    const el = $q('#sr-status');
    if (el) el.textContent = msg || '';
}

function setBusy(v) {
    busy = v;
    const b = $q('#sr-run');
    if (b) { b.disabled = v; b.textContent = v ? '生成中…' : '改写'; }
}

/** 从聊天末尾往回数第 n 条 AI 消息的下标 */
function pickTarget(which) {
    let n = which === 'last' ? 1 : which === 'prev' ? 2 : parseInt(which, 10);
    if (!Number.isFinite(n) || n < 1) n = 1;
    let seen = 0;
    for (let i = chat.length - 1; i >= 0; i--) {
        const m = chat[i];
        if (!m || m.is_user || m.is_system) continue;
        seen++;
        if (seen === n) return i;
    }
    return -1;
}

/** 去掉模型可能加的外壳 */
function clean(t) {
    t = String(t || '').trim();
    t = t.replace(/^```[a-zA-Z]*\s*\n?/, '').replace(/\n?```\s*$/, '').trim();
    t = t.replace(/^(改写后的?正文|改写后|修改后|输出|结果)\s*[:：]\s*/, '');
    t = t.replace(/^【正文】\s*/, '');
    return t.trim();
}

async function persist() {
    try { await saveChatConditional(); } catch (e) { console.warn('[剧情改写] 保存失败', e); }
    try { await reloadCurrentChat(); } catch (e) { console.warn('[剧情改写] 重载失败', e); }
}

async function run() {
    if (busy) return;
    const ins = $q('#sr-ins').value.trim();
    if (!ins) { setStatus('先写一句要改什么'); return; }

    const idx = pickTarget($q('#sr-target').value);
    if (idx < 0) { setStatus('没找到可以改的回复'); return; }

    const old = chat[idx].mes || '';
    if (!old.trim()) { setStatus('这条是空的，换一条'); return; }

    setBusy(true);
    setStatus('生成中…');
    try {
        const prompt = `${SYS}\n\n【原文】\n${old}\n\n【修改要求】\n${ins}\n\n只输出改写后的正文：`;
        const raw = await generateQuietPrompt({
            quietPrompt: prompt,
            skipWIAN: true,
            removeReasoning: true,
            responseLength: 800,
        });
        const text = clean(raw);
        if (!text) throw new Error('模型返回了空内容（可能额度又被思考吃光了）');

        st = { idx, old, text };
        $q('#sr-new').textContent = text;
        $q('#sr-old').textContent = old;
        $q('#sr-out').classList.add('sr-show');
        setStatus('改好了，确认再替换');
    } catch (e) {
        console.error('[剧情改写]', e);
        setStatus('失败：' + (e && e.message ? e.message : e));
    } finally {
        setBusy(false);
    }
}

async function apply() {
    if (st.idx < 0) return;
    lastUndo = { idx: st.idx, old: st.old };
    chat[st.idx].mes = st.text;
    await persist();
    $q('#sr-out').classList.remove('sr-show');
    $q('#sr-undo').style.display = 'inline';
    setStatus('已替换到聊天');
    st = { idx: -1, old: '', text: '' };
}

async function undo() {
    if (!lastUndo) return;
    chat[lastUndo.idx].mes = lastUndo.old;
    await persist();
    lastUndo = null;
    $q('#sr-undo').style.display = 'none';
    setStatus('已还原');
}

function buildUi() {
    if (document.getElementById('sr-panel')) return;

    const tab = document.createElement('div');
    tab.id = 'sr-tab';
    tab.textContent = '剧情改写';

    const panel = document.createElement('div');
    panel.id = 'sr-panel';
    panel.innerHTML = `
        <div id="sr-head">
            <span>剧情改写</span>
            <span class="sr-flex"></span>
            <span id="sr-close" title="收起">×</span>
        </div>
        <div id="sr-main">
            <div id="sr-target-row">
                <span>改哪条</span>
                <select id="sr-target">
                    <option value="last">最后一条回复</option>
                    <option value="prev">倒数第二条</option>
                    <option value="3">倒数第三条</option>
                </select>
            </div>
            <textarea id="sr-ins" placeholder="要改成什么样？&#10;例如：改短一半 / 加一句气味 / 这里别写死，改成擦伤 / 把这段换成许晴视角"></textarea>
            <div id="sr-bar">
                <button id="sr-run" class="sr-btn primary">改写</button>
                <button id="sr-undo" class="sr-btn" style="display:none">撤销替换</button>
                <span id="sr-status"></span>
            </div>
            <div id="sr-out">
                <div class="sr-lbl">改写结果（确认后再替换）</div>
                <div id="sr-new"></div>
                <span class="sr-link" id="sr-toggle-old">显示原文</span>
                <div id="sr-old-wrap"><div id="sr-old"></div></div>
                <div id="sr-bar">
                    <button id="sr-apply" class="sr-btn primary">替换到聊天</button>
                    <button id="sr-drop" class="sr-btn">放弃</button>
                </div>
            </div>
        </div>`;

    document.body.appendChild(tab);
    document.body.appendChild(panel);

    tab.addEventListener('click', () => panel.classList.toggle('sr-open'));
    $q('#sr-close').addEventListener('click', () => panel.classList.remove('sr-open'));
    $q('#sr-run').addEventListener('click', run);
    $q('#sr-apply').addEventListener('click', apply);
    $q('#sr-undo').addEventListener('click', undo);
    $q('#sr-drop').addEventListener('click', () => {
        $q('#sr-out').classList.remove('sr-show');
        st = { idx: -1, old: '', text: '' };
        setStatus('已放弃');
    });
    $q('#sr-toggle-old').addEventListener('click', () => {
        const w = $q('#sr-old-wrap');
        w.classList.toggle('sr-show');
        $q('#sr-toggle-old').textContent = w.classList.contains('sr-show') ? '收起原文' : '显示原文';
    });
    $q('#sr-ins').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
    });

    console.log('[剧情改写] 已加载');
}

jQuery(() => {
    buildUi();
});

const API = 'http://localhost:8765';
let selected = '';
let abortController = null;
let isSending = false;

document.getElementById('welcomeTime').textContent = new Date().toLocaleTimeString();

function togglePanel() {
    const panel = document.getElementById('controlPanel');
    const icon = document.getElementById('toggleIcon');
    panel.classList.toggle('expanded');
    icon.innerHTML = panel.classList.contains('expanded') ? '&#9650;' : '&#9660;';
    if (panel.classList.contains('expanded')) loadSnapshots();
}

function toast(msg, err = false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + (err ? 'error' : 'success');
    setTimeout(() => t.classList.remove('show'), 3000);
}

async function loadSnapshots() {
    try {
        const d = await (await fetch(`${API}/api/snapshots`)).json();
        document.getElementById('snapshotList').innerHTML =
            d.success && d.snapshots.length
                ? d.snapshots.map(s => `<div class="snapshot-item" onclick="selectSnap('${s}',this)">${s}</div>`).join('')
                : '<span style="color:#b2bec3">暂无快照</span>';
    } catch { document.getElementById('snapshotList').innerHTML = '<span style="color:#d63031">加载失败</span>'; }
}

function selectSnap(tag, el) {
    document.querySelectorAll('.snapshot-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    selected = tag;
}

async function doEvolve(apply) {
    const btn = document.getElementById(apply ? 'btn-apply' : 'btn-evolve');
    btn.disabled = true;
    toast(apply ? '执行进化中...' : '预览进化中...');
    try {
        const d = await (await fetch(`${API}/api/evolve`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({apply})
        })).json();
        toast(d.success ? (apply ? '进化已执行' : '预览完成') : '操作失败', !d.success);
        addMsg('system', apply ? '进化执行完成' : '进化预览完成');
    } catch (e) { toast('请求失败: ' + e.message, true); }
    finally { btn.disabled = false; }
}

async function takeSnapshot() {
    toast('创建快照中...');
    try {
        const d = await (await fetch(`${API}/api/snapshot/take`, {method: 'POST'})).json();
        if (d.success) { toast('快照已创建'); addMsg('system', '快照: ' + d.snapshot); loadSnapshots(); }
        else toast('创建失败', true);
    } catch (e) { toast('请求失败', true); }
}

async function doRollback() {
    if (!selected) { toast('请先选择快照', true); return; }
    if (!confirm(`确定回滚到 ${selected}？`)) return;
    toast('回滚中...');
    try {
        const d = await (await fetch(`${API}/api/rollback`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tag: selected})
        })).json();
        if (d.success) { toast('回滚成功'); addMsg('system', d.result); selected = ''; loadSnapshots(); }
        else toast('回滚失败', true);
    } catch (e) { toast('请求失败', true); }
}

function addMsg(type, content) {
    const c = document.getElementById('chatContainer');
    const m = document.createElement('div');
    m.className = 'message ' + (type === 'user' ? 'user' : type === 'error' ? 'error' : type === 'system' ? 'system' : 'assistant');
    m.innerHTML = content + `<span class="time">${new Date().toLocaleTimeString()}</span>`;
    c.appendChild(m);
    c.scrollTop = c.scrollHeight;
}

async function send() {
    const input = document.getElementById('userInput');
    const btn = document.getElementById('sendBtn');

    // 如果正在发送，点击则停止
    if (isSending) {
        if (abortController) {
            abortController.abort();
        }
        return;
    }

    const msg = input.value.trim();
    if (!msg) return;

    addMsg('user', msg);
    input.value = '';
    isSending = true;
    btn.innerHTML = '&#9632;'; // 停止方块图标
    btn.classList.add('stop');

    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.id = 'loadingIndicator';
    loading.innerHTML = '思考中 <div class="loading-dots"><span></span><span></span><span></span></div>';
    document.getElementById('chatContainer').appendChild(loading);
    document.getElementById('chatContainer').scrollTop = 1e9;

    abortController = new AbortController();

    try {
        const d = await (await fetch(`${API}/api/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg}),
            signal: abortController.signal
        })).json();
        loading.remove();
        if (d.success) addMsg('assistant', d.response);
        else addMsg('error', d.detail || '请求失败');
    } catch (e) {
        loading.remove();
        if (e.name === 'AbortError') {
            addMsg('system', '已终止当前会话');
        } else {
            addMsg('error', '连接失败，请确保服务已启动');
        }
    } finally {
        isSending = false;
        abortController = null;
        btn.innerHTML = '&#10148;'; // 发送箭头图标
        btn.classList.remove('stop');
        input.focus();
    }
}

function handleKey(e) { if (e.key === 'Enter' && !isSending) send(); }

// 设置弹窗
function openSettings() {
    // 加载当前设置
    fetch(`${API}/api/settings`)
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                document.getElementById('settingModel').value = d.settings.model || '';
                document.getElementById('settingBaseUrl').value = d.settings.base_url || '';
                document.getElementById('settingApiKey').value = d.settings.api_key || '';
            }
        })
        .catch(() => {});
    document.getElementById('settingsModal').classList.add('show');
}

function closeSettings() {
    document.getElementById('settingsModal').classList.remove('show');
}

function closeSettingsOnOverlay(e) {
    if (e.target === document.getElementById('settingsModal')) {
        closeSettings();
    }
}

async function saveSettings() {
    const model = document.getElementById('settingModel').value.trim();
    const baseUrl = document.getElementById('settingBaseUrl').value.trim();
    const apiKey = document.getElementById('settingApiKey').value.trim();

    try {
        const d = await (await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model, base_url: baseUrl, api_key: apiKey})
        })).json();

        if (d.success) {
            toast('设置已保存');
            closeSettings();
        } else {
            toast(d.detail || '保存失败', true);
        }
    } catch (e) {
        toast('保存失败: ' + e.message, true);
    }
}

// ── MCP 服务端管理 ────────────────────────────────────────
function openMcp() {
    document.getElementById('mcpModal').classList.add('show');
    cancelMcpForm();
    loadMcpList();
    document.getElementById('mcpTools').textContent = '';
}
function closeMcp() { document.getElementById('mcpModal').classList.remove('show'); }
function closeMcpOnOverlay(e) {
    if (e.target === document.getElementById('mcpModal')) closeMcp();
}

async function loadMcpList() {
    try {
        const d = await (await fetch(`${API}/api/mcp/servers`)).json();
        const list = document.getElementById('mcpList');
        if (!d.success) { list.innerHTML = '<span style="color:#d63031">加载失败</span>'; return; }
        if (!d.servers.length) { list.innerHTML = '<span style="color:#888">暂无配置，点击 + 新增</span>'; return; }
        list.innerHTML = d.servers.map(s => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px;border-bottom:1px solid #f0f0f0;">
                <div>
                    <div style="font-weight:500;">${s.name} <span style="color:${s.enabled?'#27ae60':'#999'};font-size:12px;">[${s.enabled?'启用':'禁用'}]</span> <span style="color:#888;font-size:12px;">[${s.transport||'stdio'}]</span></div>
                    <div style="color:#888;font-size:12px;">${s.transport==='http' ? (s.url||'') : ((s.command||'')+' '+((s.args||[]).join(' ')))}</div>
                    ${s.description?`<div style="color:#aaa;font-size:12px;">${s.description}</div>`:''}
                </div>
                <div style="display:flex;gap:4px;">
                    <button class="modal-btn modal-btn-secondary" onclick='toggleMcp(${s.id}, ${!s.enabled})'>${s.enabled?'禁用':'启用'}</button>
                    <button class="modal-btn modal-btn-secondary" onclick='editMcp(${JSON.stringify(s).replace(/'/g, "&#39;")})'>编辑</button>
                    <button class="modal-btn modal-btn-secondary" onclick='deleteMcp(${s.id})' style="color:#d63031;">删除</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('mcpList').innerHTML = '<span style="color:#d63031">网络错误</span>';
    }
}

function showMcpForm() {
    document.getElementById('mcpForm').style.display = 'block';
    document.getElementById('mcpFormId').value = '';
    document.getElementById('mcpName').value = '';
    document.getElementById('mcpTransport').value = 'http';
    document.getElementById('mcpUrl').value = 'http://localhost:8801/mcp';
    document.getElementById('mcpCommand').value = '';
    document.getElementById('mcpArgs').value = '[]';
    document.getElementById('mcpEnv').value = '{}';
    document.getElementById('mcpDesc').value = '';
    document.getElementById('mcpEnabled').checked = true;
    onMcpTransportChange();
}
function cancelMcpForm() { document.getElementById('mcpForm').style.display = 'none'; }

function onMcpTransportChange() {
    const t = document.getElementById('mcpTransport').value;
    document.getElementById('mcpUrlGroup').style.display  = (t === 'http')  ? '' : 'none';
    document.getElementById('mcpCmdGroup').style.display  = (t === 'stdio') ? '' : 'none';
    document.getElementById('mcpArgsGroup').style.display = (t === 'stdio') ? '' : 'none';
}

function editMcp(s) {
    document.getElementById('mcpForm').style.display = 'block';
    document.getElementById('mcpFormId').value = s.id;
    document.getElementById('mcpName').value = s.name || '';
    document.getElementById('mcpTransport').value = s.transport || 'http';
    document.getElementById('mcpUrl').value = s.url || '';
    document.getElementById('mcpCommand').value = s.command || '';
    document.getElementById('mcpArgs').value = JSON.stringify(s.args || []);
    document.getElementById('mcpEnv').value = JSON.stringify(s.env || {});
    document.getElementById('mcpDesc').value = s.description || '';
    document.getElementById('mcpEnabled').checked = !!s.enabled;
    onMcpTransportChange();
}

async function saveMcp() {
    let args, env;
    try { args = JSON.parse(document.getElementById('mcpArgs').value || '[]'); }
    catch { toast('args 必须是合法 JSON 数组', true); return; }
    try { env = JSON.parse(document.getElementById('mcpEnv').value || '{}'); }
    catch { toast('env 必须是合法 JSON 对象', true); return; }

    const transport = document.getElementById('mcpTransport').value;
    const body = {
        name: document.getElementById('mcpName').value.trim(),
        transport,
        url: document.getElementById('mcpUrl').value.trim(),
        command: document.getElementById('mcpCommand').value.trim(),
        args, env,
        description: document.getElementById('mcpDesc').value.trim(),
        enabled: document.getElementById('mcpEnabled').checked ? 1 : 0,
    };
    if (!body.name) { toast('name 不能为空', true); return; }
    if (transport === 'http' && !body.url) { toast('http 协议必须填写 url', true); return; }
    if (transport === 'stdio' && !body.command) { toast('stdio 协议必须填写 command', true); return; }

    const id = document.getElementById('mcpFormId').value;
    const url = id ? `${API}/api/mcp/servers/${id}` : `${API}/api/mcp/servers`;
    const method = id ? 'PUT' : 'POST';
    try {
        const d = await (await fetch(url, {
            method, headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        })).json();
        if (d.success) { toast('已保存'); cancelMcpForm(); loadMcpList(); }
        else toast(d.detail || '保存失败', true);
    } catch (e) { toast('保存失败: ' + e.message, true); }
}

async function toggleMcp(id, enabled) {
    try {
        const d = await (await fetch(`${API}/api/mcp/servers/${id}/toggle`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled}),
        })).json();
        if (d.success) { toast('已切换'); loadMcpList(); }
        else toast(d.detail || '失败', true);
    } catch (e) { toast('失败: ' + e.message, true); }
}

async function deleteMcp(id) {
    if (!confirm('确定删除该 MCP 服务端配置？')) return;
    try {
        const d = await (await fetch(`${API}/api/mcp/servers/${id}`, {method: 'DELETE'})).json();
        if (d.success) { toast('已删除'); loadMcpList(); }
        else toast(d.detail || '失败', true);
    } catch (e) { toast('失败: ' + e.message, true); }
}

async function reloadMcp() {
    toast('重新连接中...');
    try {
        const d = await (await fetch(`${API}/api/mcp/reload`, {method: 'POST'})).json();
        if (d.success) toast(`已重连，工具数: ${d.tools}`);
        else toast(d.detail || '失败', true);
    } catch (e) { toast('失败: ' + e.message, true); }
}

async function loadMcpTools() {
    try {
        const d = await (await fetch(`${API}/api/mcp/tools`)).json();
        const box = document.getElementById('mcpTools');
        if (!d.success) { box.textContent = '加载失败'; return; }
        if (!d.tools.length) { box.textContent = '当前未加载任何 MCP 工具'; return; }
        box.innerHTML = '<b>已加载工具：</b><br>' + d.tools.map(t =>
            `<div style="margin:4px 0;"><code>${t.name}</code> — <span style="color:#666;">${t.description||''}</span></div>`
        ).join('');
    } catch (e) {
        document.getElementById('mcpTools').textContent = '网络错误';
    }
}
/* ============================================================
   多模态采集板上位机 — 公共脚本
   主题切换逻辑已内联到 base.html，这里不再重复
   ============================================================ */

// ---- SSE 实时数据流 ----
let evtSource = null;
let isRecording = false;
const globalState = {
    ecg: [[], [], [], []],
    piezo: [[], []],
    matrix: new Array(16).fill(0),
    hr: 72,
    rr: 16,
    isRecording: false,
    recordFile: null,
    matrixMode: 'resistance',
};

const MAX_POINTS = 500; // 5s * 100Hz

function connectStream() {
    if (evtSource) evtSource.close();
    evtSource = new EventSource('/stream');
    evtSource.addEventListener('sample', (e) => {
        const data = JSON.parse(e.data);
        data.samples.forEach(s => {
            // ECG
            for (let i = 0; i < 4; i++) {
                globalState.ecg[i].push(s.ecg[i]);
                if (globalState.ecg[i].length > MAX_POINTS) globalState.ecg[i].shift();
            }
            // Piezo
            for (let i = 0; i < 2; i++) {
                globalState.piezo[i].push(s.piezo[i]);
                if (globalState.piezo[i].length > MAX_POINTS) globalState.piezo[i].shift();
            }
            // Matrix
            globalState.matrix = s.matrix;
            // HR
            if (s.hr) {
                globalState.hr = s.hr;
                globalState.rr = Math.round(s.hr / 4.5);
            }
        });
        globalState.isRecording = data.is_recording;
        globalState.recordFile = data.record_file;
        globalState.matrixMode = data.matrix_mode;
        updateRecordUI();
        if (typeof onSample === 'function') onSample();
    });
    evtSource.onerror = () => { console.warn('SSE 断开，5s 后重连'); setTimeout(connectStream, 5000); };
}

function updateRecordUI() {
    const pill = document.getElementById('connPill');
    if (pill) {
        const dot = pill.querySelector('.dot');
        dot.style.background = globalState.isRecording ? 'var(--accent-warning)' : 'var(--accent-success)';
        dot.style.boxShadow = `0 0 6px ${globalState.isRecording ? 'var(--accent-warning)' : 'var(--accent-success)'}`;
    }
}

// ---- 记录控制 ----
const recBtn = document.getElementById('recBtn');
if (recBtn) {
    recBtn.addEventListener('click', async () => {
        if (globalState.isRecording) {
            const r = await fetch('/api/record/stop', { method: 'POST' });
            const d = await r.json();
            recBtn.textContent = '● 记录';
            recBtn.classList.remove('btn-danger');
        } else {
            const name = `record_${Date.now()}`;
            const r = await fetch('/api/record/start', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const d = await r.json();
            if (d.ok) {
                recBtn.textContent = '■ 停止';
                recBtn.classList.add('btn-danger');
            }
        }
    });
}

// ---- 导出 ----
const exportCsvBtn = document.getElementById('exportCsvBtn');
if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', async () => {
        const r = await fetch('/api/records');
        const d = await r.json();
        if (d.length > 0) {
            window.open(`/data/${d[d.length - 1].filename}`, '_blank');
        } else {
            alert('暂无记录文件');
        }
    });
}

const exportPngBtn = document.getElementById('exportPngBtn');
if (exportPngBtn) {
    exportPngBtn.addEventListener('click', () => {
        const canvas = document.getElementById('ecgCanvas');
        if (canvas) {
            const link = document.createElement('a');
            link.download = `ecg_${Date.now()}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        }
    });
}

// ---- 开始/停止 ----
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
if (startBtn) startBtn.addEventListener('click', () => connectStream());
if (stopBtn) stopBtn.addEventListener('click', () => { if (evtSource) evtSource.close(); });

// 自动连接
connectStream();

// ---- 工具函数 ----
function mapValue(val, inMin, inMax, outMin, outMax) {
    return (val - inMin) / (inMax - inMin) * (outMax - outMin) + outMin;
}

function lerpColor(t) {
    // 蓝 → 紫 → 橙 → 红
    const stops = [[27, 111, 249], [99, 85, 255], [255, 122, 69], [229, 69, 61]];
    const seg = t * (stops.length - 1);
    const i = Math.min(Math.floor(seg), stops.length - 2);
    const f = seg - i;
    const [r1, g1, b1] = stops[i];
    const [r2, g2, b2] = stops[i + 1];
    return `rgb(${Math.round(r1 + (r2 - r1) * f)},${Math.round(g1 + (g2 - g1) * f)},${Math.round(b1 + (b2 - b1) * f)})`;
}

function fmtTime(d = new Date()) {
    const p = n => String(n).padStart(2, '0');
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* Diagram Workflow SPA — vanilla JS, no build step. */
const App = (() => {
  let current = null, detail = null, manifest = null, pollTimer = null, pendingFiles = [];
  let selVer = null, cmpMode = false, cmpA = null, cmpB = null, folderName = '', histView = false, planCache = null;

  // ---------- inline SVG icons (no external assets) ----------
  const P = {
    plus: 'M12 5v14M5 12h14',
    folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
    upload: 'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M12 3v12M7.5 7.5 12 3l4.5 4.5',
    spark: 'M12 3l1.7 4.6L18.5 9.3l-4.8 1.7L12 16l-1.7-5L5.5 9.3l4.8-1.7zM19 14l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z',
    check: 'M20 6 9 17l-5-5',
    arrow: 'M5 12h14M13 6l6 6-6 6',
    download: 'M12 3v12M7 10l5 5 5-5M5 21h14',
    trash: 'M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13',
    doc: 'M14 3v5h5M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z',
    image: 'M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3M21 15l-5-5L5 21',
    zoom: 'M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7',
    edit: 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z',
    code: 'M16 18l6-6-6-6M8 6l-6 6 6 6',
    info: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M12 16v-5M12 8h.01',
    chevron: 'M9 6l6 6-6 6',
    warn: 'M10.3 3.5 1.7 18a2 2 0 0 0 1.7 3h17.2a2 2 0 0 0 1.7-3L13.7 3.5a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01',
    clock: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M12 6v6l4 2',
    layers: 'M12 2 2 7l10 5 10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
    doc2: 'M14 3v5h5M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM9 13h6M9 17h4',
    diagram: 'M5 3h5v5H5zM14 16h5v5h-5zM7.5 8v3a2 2 0 0 0 2 2h5M16.5 16v-1a2 2 0 0 0-2-2',
    play: 'M6 4l14 8-14 8z',
    grid: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
    rocket: 'M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M9 11a5 5 0 0 1 3-3c4-1 8 0 8 0s1 4 0 8a5 5 0 0 1-3 3l-3-3-2-2zM15 9h.01',
  };
  const ic = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24"><path d="${P[name]}"/></svg>`;

  const $ = (s, r = document) => r.querySelector(s);
  const el = (h) => { const t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstChild; };
  const esc = (s) => (s == null ? '' : String(s)).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ---------- custom modals (replace browser confirm/prompt) ----------
  function modalConfirm({ title, message, okText = 'Confirm', danger = false }) {
    return new Promise(resolve => {
      const ov = el(`<div class="modal-ov"><div class="modal">
        <div class="modal-head ${danger ? 'danger' : ''}"><div class="mi">${ic(danger ? 'trash' : 'info')}</div><h3>${esc(title)}</h3></div>
        <div class="modal-body">${esc(message)}</div>
        <div class="modal-foot"><button class="btn ghost" data-a="c">Cancel</button>
          <button class="btn ${danger ? 'danger-solid' : 'primary'}" data-a="ok">${esc(okText)}</button></div>
      </div></div>`);
      const done = v => { ov.remove(); document.removeEventListener('keydown', key); resolve(v); };
      const key = e => { if (e.key === 'Escape') done(false); if (e.key === 'Enter') done(true); };
      ov.addEventListener('mousedown', e => { if (e.target === ov) done(false); });
      ov.querySelector('[data-a=c]').onclick = () => done(false);
      ov.querySelector('[data-a=ok]').onclick = () => done(true);
      document.body.appendChild(ov); document.addEventListener('keydown', key);
      setTimeout(() => ov.querySelector('[data-a=ok]').focus(), 30);
    });
  }
  function modalPrompt({ title, message = '', value = '', placeholder = '', okText = 'Create' }) {
    return new Promise(resolve => {
      const ov = el(`<div class="modal-ov"><div class="modal">
        <div class="modal-head"><div class="mi">${ic('edit')}</div><h3>${esc(title)}</h3></div>
        <div class="modal-body">${message ? esc(message) : ''}<input type="text" id="m-in" placeholder="${esc(placeholder)}" value="${esc(value)}"></div>
        <div class="modal-foot"><button class="btn ghost" data-a="c">Cancel</button>
          <button class="btn primary" data-a="ok">${esc(okText)}</button></div>
      </div></div>`);
      const inp = () => ov.querySelector('#m-in');
      const done = v => { ov.remove(); document.removeEventListener('keydown', key); resolve(v); };
      const ok = () => done(inp().value.trim() || null);
      const key = e => { if (e.key === 'Escape') done(null); if (e.key === 'Enter') { e.preventDefault(); ok(); } };
      ov.addEventListener('mousedown', e => { if (e.target === ov) done(null); });
      ov.querySelector('[data-a=c]').onclick = () => done(null);
      ov.querySelector('[data-a=ok]').onclick = ok;
      document.body.appendChild(ov); document.addEventListener('keydown', key);
      setTimeout(() => { const i = inp(); i.focus(); i.select(); }, 30);
    });
  }

  function openHelp() {
    const steps = [
      ['plus', 'Create a workspace &amp; pick a type', 'Click <b>New workspace</b> and choose what to make: a <b>Diagram</b> (one SA-grade diagram, fast local render) or a <b>Technical Proposal</b> (a full <b>.docx</b> from a folder of RFP + docs). Each workspace keeps its own inputs, versions and output.'],
      ['edit', 'Describe the diagram', 'Type a plain-language prompt (e.g. “our AWS setup for a ride-hailing backend”, “the checkout sequence with the payment gateway”, “the order lifecycle state machine”). Optionally add docs: drag files onto the box, <b>Choose files</b>, <b>Upload a folder</b>, or <b>Browse…</b> a folder on this machine.'],
      ['spark', 'Refine', 'Click <b>Refine spec</b>. The real skill runs head-less via the <code>claude</code> CLI (usually 3–5 minutes): it reads the diagram knowledge base and designs a rigorous, standards-based spec, then stops for your review. You can watch the job log while it works.'],
      ['check', 'Review &amp; confirm', 'At the gate, check the proposed diagram(s) and the rationale. Fine-tune the spec JSON if you like (advanced), or <b>Edit inputs &amp; re-refine</b>. When happy, click <b>Generate diagrams</b>.'],
      ['grid', 'Preview &amp; formats', 'Each render appears as a tile. Open any format: <b>PNG</b> (sharp image), <b>SVG</b> (vector), editable <b>.drawio</b>, or a Word <b>.docx</b> with the figure and description. Click an image to zoom.'],
      ['code', 'Versions &amp; compare', 'Every <b>Generate</b> is saved as a numbered <b>version</b>. Use the version timeline to view any one; click <b>Compare</b> to see two side by side with their self-check results and pick the better one. The <b>Version history</b> card is reachable from any screen.'],
      ['play', 'Iterate', '<b>Iterate from vN</b> loads that version’s spec back so you can tweak it and regenerate — that becomes a new version, so nothing is ever lost. <b>Edit inputs</b> changes the prompt/docs and re-refines.'],
      ['download', 'Export', '<b>Export vN</b> downloads a zip of that version: PNG + SVG + .drawio + .docx + a diagrams.json manifest.'],
    ];
    const tips = [
      'Your place is saved in the address bar — press <b>F5</b> and the same workspace reopens (you can bookmark it too).',
      'Refine needs the <code>claude</code> CLI signed in once. <b>Generate / Preview / Export</b> work without it.',
      'All times are shown in your machine’s local timezone.',
    ];
    const stepHTML = steps.map((s, i) => `<div class="help-step"><div class="hs-n">${ic(s[0])}</div>
      <div><div class="hs-t">${i + 1}. ${s[1]}</div><div class="hs-b">${s[2]}</div></div></div>`).join('');
    const ov = el(`<div class="modal-ov"><div class="modal wide">
      <div class="modal-head"><div class="mi">${ic('info')}</div><h3>How to use Diagram Workflow</h3></div>
      <div class="modal-body help-body">
        <p>Turn a plain-language idea into a senior-SA-grade <b>diagram</b>, or a folder of RFP docs into a full <b>technical proposal .docx</b> — analysed, confirmed by you at a gate, generated, versioned, and exportable. The steps below apply to both (a proposal analyses a document folder instead of a prompt, and produces a .docx).</p>
        <div class="help-steps">${stepHTML}</div>
        <div class="help-tips"><div class="hs-t">Good to know</div><ul>${tips.map(t => `<li>${t}</li>`).join('')}</ul></div>
      </div>
      <div class="modal-foot"><button class="btn primary" data-a="ok">Got it</button></div>
    </div></div>`);
    const done = () => { ov.remove(); document.removeEventListener('keydown', key); };
    const key = e => { if (e.key === 'Escape') done(); };
    ov.addEventListener('mousedown', e => { if (e.target === ov) done(); });
    ov.querySelector('[data-a=ok]').onclick = done;
    document.body.appendChild(ov); document.addEventListener('keydown', key);
  }

  let toastT = null;
  function toast(msg, isErr = false) {
    const t = $('#toast');
    t.innerHTML = (isErr ? ic('warn') : ic('check')) + esc(msg);
    t.className = 'toast show' + (isErr ? ' err' : '');
    clearTimeout(toastT);
    toastT = setTimeout(() => t.classList.remove('show'), isErr ? 5200 : 2600);
  }

  async function api(method, path, body, isForm = false) {
    const opt = { method, headers: {} };
    if (body && !isForm) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    if (body && isForm) opt.body = body;
    const r = await fetch(path, opt);
    if (!r.ok) { let d; try { d = await r.json(); } catch { d = { detail: r.statusText }; } throw new Error(d.detail || ('HTTP ' + r.status)); }
    const ct = r.headers.get('content-type') || '';
    return ct.includes('json') ? r.json() : r.text();
  }

  // ---------- workspace list ----------
  async function loadList() {
    const items = await api('GET', '/api/workspaces');
    $('#ws-count').textContent = items.length;
    const box = $('#ws-list'); box.innerHTML = '';
    if (!items.length) { box.appendChild(el('<div class="side-empty">No workspaces yet.<br>Create one to begin.</div>')); return; }
    items.forEach(w => {
      const tb = w.type === 'proposal' ? '<span class="tbadge proposal">Proposal</span>' : '<span class="tbadge diagram">Diagram</span>';
      const node = el(`<div class="ws-item ${w.id === current ? 'active' : ''}" data-id="${w.id}">
        <div class="n">${esc(w.name)}</div>
        <div class="meta">${tb}<span class="pill ${w.status}">${w.status}</span>${w.n_diagrams ? `<span>· ${w.n_diagrams}</span>` : ''}</div></div>`);
      node.onclick = () => select(w.id);
      box.appendChild(node);
    });
  }

  function modalNewWorkspace() {
    return new Promise(resolve => {
      let type = null;
      const ov = el(`<div class="modal-ov"><div class="modal wide">
        <div class="modal-head"><div class="mi">${ic('plus')}</div><h3>New workspace</h3></div>
        <div class="modal-body">
          <div class="wtype-q">What do you want to create?</div>
          <div class="wtype-grid">
            <button class="wtype" data-t="diagram" type="button"><div class="wt-ic">${ic('diagram')}</div>
              <div class="wt-t">Diagram</div><div class="wt-d">One SA-grade diagram from a prompt or docs. Fast, local render.</div></button>
            <button class="wtype" data-t="proposal" type="button"><div class="wt-ic">${ic('doc2')}</div>
              <div class="wt-t">Technical Proposal</div><div class="wt-d">A full proposal <b>.docx</b> from a folder of RFP + docs.</div></button>
          </div>
          <div class="field" style="margin-top:16px"><label>Name</label>
            <input type="text" id="nw-name" placeholder="e.g. Payments Platform"></div>
        </div>
        <div class="modal-foot"><button class="btn ghost" data-a="c">Cancel</button>
          <button class="btn primary" data-a="ok" disabled>Create</button></div>
      </div></div>`);
      const okBtn = ov.querySelector('[data-a=ok]'), nameIn = ov.querySelector('#nw-name');
      ov.querySelectorAll('.wtype').forEach(b => b.onclick = () => {
        type = b.dataset.t;
        ov.querySelectorAll('.wtype').forEach(x => x.classList.toggle('on', x === b));
        okBtn.disabled = false;
        if (!nameIn.value.trim()) nameIn.value = type === 'proposal' ? 'Untitled proposal' : 'Untitled diagram';
        nameIn.focus();
      });
      const done = v => { ov.remove(); document.removeEventListener('keydown', key); resolve(v); };
      const ok = () => { if (!type) return; done({ name: nameIn.value.trim() || (type === 'proposal' ? 'Untitled proposal' : 'Untitled diagram'), type }); };
      const key = e => { if (e.key === 'Escape') done(null); if (e.key === 'Enter' && type) { e.preventDefault(); ok(); } };
      ov.addEventListener('mousedown', e => { if (e.target === ov) done(null); });
      ov.querySelector('[data-a=c]').onclick = () => done(null);
      okBtn.onclick = ok;
      document.body.appendChild(ov);
      document.addEventListener('keydown', key);
    });
  }
  async function newWorkspace() {
    const res = await modalNewWorkspace();
    if (!res) return;
    const w = await api('POST', '/api/workspaces', { name: res.name, type: res.type });
    await loadList(); select(w.id);
  }

  async function select(id) {
    current = id; pendingFiles = []; manifest = null; folderName = '';
    selVer = null; cmpMode = false; cmpA = cmpB = null; histView = false; stopPoll();
    if ((location.hash || '').slice(1) !== id) location.hash = id;   // remember across F5
    await refresh();
    document.querySelectorAll('.ws-item').forEach(n => n.classList.toggle('active', n.dataset.id === id));
  }
  function showEmpty() {
    current = null; detail = null; stopPoll();
    if (location.hash) location.hash = '';
    $('#ws-view').classList.add('hidden'); $('#empty').classList.remove('hidden');
    document.querySelectorAll('.ws-item').forEach(n => n.classList.remove('active'));
  }

  async function refresh() {
    if (!current) return;
    const prevStatus = detail && detail.status;
    detail = await api('GET', '/api/workspaces/' + current);
    render();
    if (detail.status !== prevStatus) loadList();   // keep the sidebar pill live (no F5 needed)
    const busy = ['refining', 'generating'].includes(detail.status) || (detail.job && detail.job.running);
    if (busy) startPoll(); else stopPoll();
  }
  function startPoll() { if (!pollTimer) pollTimer = setInterval(refresh, 1500); }
  function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  // ---------- stepper ----------
  const STEPS = ['Inputs', 'Refine', 'Confirm', 'Generate', 'Preview'];
  function stepIndex(status) { return { new: 0, refining: 1, refined: 2, generating: 3, generated: 4, error: -1 }[status] ?? 0; }
  function stepper(status) {
    let active = stepIndex(status);
    const busy = status === 'refining' || status === 'generating';
    if (status === 'error') active = stepIndex(detail.job?.phase === 'generate' ? 'generating' : 'refining');
    let h = '<div class="stepper">';
    STEPS.forEach((s, i) => {
      const cls = i < active ? 'done' : i === active ? 'active' : '';
      const inner = i < active ? ic('check') : (i + 1);
      h += `<div class="snode ${cls}"><div class="circle">${inner}</div><div class="lbl">${s}</div></div>`;
      if (i < STEPS.length - 1) {
        const bc = i < active ? 'done' : (i === active && busy ? 'active' : '');
        h += `<div class="sbar ${bc}"></div>`;
      }
    });
    return h + '</div>';
  }

  // ---------- render ----------
  function render() {
    $('#empty').classList.add('hidden');
    const v = $('#ws-view'); v.classList.remove('hidden');
    const d = detail;
    // show the creation time in the user's own machine timezone (not UTC)
    let created = d.created || '';
    try { const dt = new Date(d.created); if (!isNaN(dt)) created = dt.toLocaleString(); } catch (e) {}
    const tbadge = d.type === 'proposal' ? '<span class="tbadge proposal">Technical Proposal</span>' : '<span class="tbadge diagram">Diagram</span>';
    let body = `<div class="ws-head">
        <input class="ws-title" id="ws-title" value="${esc(d.name)}" readonly>
        ${tbadge}<span class="pill ${d.status}">${d.status}</span><div class="spacer"></div>
        <button class="btn danger" onclick="App.del()">${ic('trash')} Delete</button></div>
      <div class="ws-sub">${ic('layers')}<span>${d.mode} mode</span><span class="sep">•</span>${ic('clock')}<span>created ${esc(created)}</span></div>`;
    body += stepper(d.status);
    if (d.error) body += `<div class="errbox">${ic('warn')}<span>${esc(d.error)}</span></div>`;

    const isProp = d.type === 'proposal';
    const versions = d.versions || [];
    if (histView && versions.length) {
      body += isProp ? viewProposalPreview() : viewPreview();
    } else {
      if (d.status === 'new') body += viewInputs();
      else if (d.status === 'refining') body += isProp
        ? viewWorking('Analyzing the RFP + docs', 'Running the technical-proposal skill (Phase 0–3) via the claude CLI: it ingests the docs and proposes a tech stack + architecture, then stops for your review. Usually a few minutes.')
        : viewWorking('Refining your request', 'Running the skill via the claude CLI to build a rigorous spec. This usually takes 3–5 minutes — it reads the diagram knowledge base and designs the spec, then stops for your review.');
      else if (d.status === 'refined') body += isProp ? viewProposalReview() : viewReview();
      else if (d.status === 'generating') body += isProp
        ? viewWorking('Building the proposal', 'Drawing the diagrams, assembling the .docx, and running the strict format review. This is a big agent run — it can take 10–30 minutes. You can watch the job log.')
        : viewWorking('Rendering diagrams', 'Deterministic local renderers: PNG + SVG + editable .drawio + Word .docx.');
      else if (d.status === 'generated') body += isProp ? viewProposalPreview() : viewPreview();
      else if (d.status === 'error') body += viewError();
      if (versions.length && d.status !== 'generated') body += viewHistoryStrip();
    }

    v.innerHTML = body;
    if (!histView && d.status === 'new') wireInputs();
    if (!histView && d.status === 'refined') { if (isProp) loadPlanInto(); else loadManifestInto(); }
  }

  // ---------- INPUTS ----------
  function viewInputs() {
    const isProp = detail.type === 'proposal';
    return `<div class="card">
      <div class="card-head"><div class="hi">${ic(isProp ? 'doc2' : 'edit')}</div><div>
        <h3>${isProp ? 'Describe the project (or add docs)' : 'Describe the diagram'}</h3>
        <div class="sub">${isProp ? 'Describe the requirements in your own words, or upload a folder of RFP + supporting docs — either works. The skill analyses them and proposes a stack + architecture.' : 'A plain-language idea, uploaded docs, or a folder — anything works.'}</div></div></div>
      <div class="card-body">
        <div class="field">
          <label>${isProp ? 'Project / requirements' : 'Prompt'} <span class="hint">${isProp ? 'the RFP in your own words (used as-is if you don’t add docs), or extra context if you do' : 'plain language — it gets refined into a proper spec'}</span></label>
          <textarea id="in-prompt" rows="${isProp ? 5 : 4}" placeholder="${isProp ? 'e.g. Multi-tenant compliance SaaS on Azure for ~400 institutional clients. Self-service tenant onboarding &lt;4h, per-region data residency, 99.95% API SLA, 10-year tamper-evident audit. Client mandates Azure + Java, existing Azure DevOps.' : 'e.g. our AWS setup for a ride-hailing backend · the checkout sequence with the payment gateway · the order lifecycle state machine'}">${esc(detail.prompt || '')}</textarea>
        </div>
        <div class="field">
          <label>${isProp ? 'Project docs (RFP + supporting)' : 'Add project docs'} <span class="hint">${isProp ? 'optional — .pdf .docx .doc .txt .md .xlsx (recommended for a richer proposal)' : 'optional — .md .txt .pdf .docx .xlsx (ingested &amp; analysed like an RFP)'}</span></label>
          <div class="drop" id="drop">${ic('upload')}<div class="big">Drag files here</div><div class="small">or use the buttons below</div></div>
          <input type="file" id="filepick" multiple style="display:none">
          <input type="file" id="folderpick" webkitdirectory directory multiple style="display:none">
          <div class="row" style="margin-top:10px">
            <button class="btn sm" type="button" onclick="App.pickFiles()">${ic('doc')} Choose files</button>
            <button class="btn sm" type="button" onclick="App.pickFolder()">${ic('folder')} Upload a folder</button>
          </div>
          <div class="filechips" id="chips"></div>
        </div>
        <div class="field">
          <label>…or point at a folder on this machine <span class="hint">optional — no upload; the server reads it directly</span></label>
          <div class="row">
            <div class="input-ico" style="flex:1;min-width:220px">${ic('folder')}<input type="text" id="in-folder" placeholder="Click Browse, or paste a path…" value="${esc(detail.folder || '')}"></div>
            <button class="btn" type="button" onclick="App.browseFolder()">${ic('folder')} Browse…</button>
          </div>
        </div>
      </div>
      <div class="card-foot"><div class="spacer"></div>
        <button class="btn primary lg" onclick="App.saveAndRefine()">${ic('spark')} ${isProp ? 'Analyze' : 'Refine spec'}</button></div>
    </div>`;
  }
  const DOC_EXT = ['txt', 'md', 'markdown', 'csv', 'json', 'yaml', 'yml', 'docx', 'xlsx', 'xlsm', 'pdf'];
  function wireInputs() {
    const drop = $('#drop'), pick = $('#filepick'), fpick = $('#folderpick'); if (!drop) return;
    drop.onclick = () => pick.click();
    pick.onchange = () => addFiles(pick.files);
    if (fpick) fpick.onchange = () => addFolder(fpick.files);
    ['dragover', 'dragenter'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', ev => addFiles(ev.dataTransfer.files));
    renderChips();
  }
  function pickFiles() { $('#filepick')?.click(); }
  function pickFolder() { $('#folderpick')?.click(); }
  async function browseFolder() {
    toast('Opening folder picker…');
    try {
      const r = await api('GET', '/api/pick-folder');
      if (r.path) { const i = $('#in-folder'); if (i) i.value = r.path; toast('Selected ' + r.path); }
      else toast('No folder selected');
    } catch (e) { toast('Native picker unavailable — type the path', true); }
  }
  function addFiles(fl) { for (const f of fl) pendingFiles.push(f); renderChips(); }
  function addFolder(fl) {
    const files = [...fl].filter(f => DOC_EXT.includes((f.name.split('.').pop() || '').toLowerCase()));
    if (files.length) {
      folderName = (files[0].webkitRelativePath || '').split('/')[0] || 'folder';
      files.forEach(f => pendingFiles.push(f));
    }
    const skipped = fl.length - files.length;
    renderChips();
    if (files.length) toast(`Added ${files.length} doc(s) from “${folderName}”${skipped ? ` (skipped ${skipped})` : ''}`);
    else toast('No supported docs (.md/.pdf/.docx/.xlsx…) in that folder', true);
  }
  function renderChips() {
    const box = $('#chips'); if (!box) return;
    const ex = (detail.inputs || []).map(n => `<span class="filechip saved">${ic('check')}${esc(n)}</span>`);
    const st = pendingFiles.map((f, i) => `<span class="filechip">${ic('doc')}${esc(f.name)} <a href="#" onclick="App.rmFile(${i});return false">✕</a></span>`);
    box.innerHTML = ex.concat(st).join('');
  }
  function rmFile(i) { pendingFiles.splice(i, 1); renderChips(); }
  async function saveAndRefine() {
    if (health && (!health.claude_installed || !health.logged_in)) {
      await checkHealth();  // re-check in case they just signed in
      if (health && (!health.claude_installed || !health.logged_in)) {
        toast(health.claude_installed ? 'Not signed in — run `claude auth login`, then reload' : 'Install the claude CLI first, then reload', true);
        return;
      }
    }
    try {
      const fd = new FormData();
      fd.append('prompt', $('#in-prompt').value.trim());
      fd.append('folder', $('#in-folder').value.trim());
      pendingFiles.forEach(f => fd.append('files', f));
      await api('POST', '/api/workspaces/' + current + '/inputs', fd, true);
      pendingFiles = [];
      await api('POST', '/api/workspaces/' + current + '/refine');
      toast('Refining your spec…'); await refresh();
    } catch (e) { toast(e.message, true); }
  }

  // ---------- WORKING ----------
  function viewWorking(title, sub) {
    const log = (detail.job?.log || []).map(esc).join('\n');
    return `<div class="card"><div class="card-body">
      <div class="working"><div class="orbit"></div><div><div class="wt">${title}</div><div class="ws">${sub}</div></div></div></div>
      ${log ? `<div class="log"><div class="log-head"><span class="tl"><i></i><i></i><i></i></span> job log</div><pre id="joblog">${log}</pre></div>` : ''}
    </div>`;
  }

  // ---------- REVIEW ----------
  function viewReview() {
    return `<div class="card">
      <div class="card-head"><div class="hi">${ic('check')}</div><div><h3>Review the refined spec</h3><div class="sub">Confirm or edit before rendering — this is your gate.</div></div></div>
      <div class="card-body" id="review-body"><div class="working"><div class="orbit"></div><div class="wt">Loading spec…</div></div></div>
    </div>`;
  }
  async function loadManifestInto() {
    try { manifest = await api('GET', '/api/workspaces/' + current + '/manifest'); }
    catch (e) { $('#review-body').innerHTML = `<div class="errbox">${ic('warn')}<span>${esc(e.message)}</span></div>`; return; }
    const cards = (manifest.diagrams || []).map(dg => `
      <div class="dgram"><div class="dh"><span class="kindtag">${esc(dg.kind)}</span><span class="t">${esc(dg.title || dg.slug)}</span></div>
        <div class="rat">${esc(dg.rationale || '')}</div></div>`).join('');
    $('#review-body').innerHTML = `
      ${manifest.summary ? `<div class="summary">${ic('info')}<span>${esc(manifest.summary)}</span></div>` : ''}
      <div class="review-count">${(manifest.diagrams || []).length} diagram(s) proposed</div>
      ${cards}
      <details class="spec-edit"><summary>${ic('chevron')} Edit spec JSON (advanced)</summary>
        <textarea class="mono" id="manifest-json" rows="15" style="margin-top:12px">${esc(JSON.stringify(manifest, null, 2))}</textarea>
        <div class="row end" style="margin-top:10px"><button class="btn sm" onclick="App.saveManifest()">${ic('check')} Save edits</button></div>
      </details>
      <div class="row" style="margin-top:22px">
        <button class="btn ghost" onclick="App.backToInputs()">${ic('edit')} Edit inputs &amp; re-refine</button>
        <div class="spacer"></div>
        <button class="btn primary lg" onclick="App.generate()">${ic('play')} Generate diagrams</button>
      </div>`;
  }
  async function saveManifest() {
    try { const p = JSON.parse($('#manifest-json').value); await api('PUT', '/api/workspaces/' + current + '/manifest', p); manifest = p; toast('Spec saved'); }
    catch (e) { toast('Invalid JSON: ' + e.message, true); }
  }

  // ---------- PROPOSAL: plan gate ----------
  function viewProposalReview() {
    return `<div class="card">
      <div class="card-head"><div class="hi">${ic('check')}</div><div><h3>Review the proposal plan</h3><div class="sub">Confirm the stack, architecture and diagrams before the (long) generate step.</div></div></div>
      <div class="card-body" id="plan-body"><div class="working"><div class="orbit"></div><div class="wt">Loading plan…</div></div></div>
    </div>`;
  }
  async function loadPlanInto() {
    let plan;
    try { plan = await api('GET', '/api/workspaces/' + current + '/plan'); }
    catch (e) { $('#plan-body').innerHTML = `<div class="errbox">${ic('warn')}<span>${esc(e.message)}</span></div>`; return; }
    planCache = plan;
    const stack = (plan.tech_stack || []).map(s => `<tr><td>${esc(s.layer)}</td><td><b>${esc(s.choice)}</b></td><td>${esc(s.rationale || '')}</td></tr>`).join('');
    const dgs = (plan.diagrams || []).map(dd => `<div class="dgram"><div class="dh"><span class="kindtag">${esc(dd.kind || '')}</span><span class="t">${esc(dd.title || dd.slug)}</span></div><div class="rat">${esc(dd.purpose || '')}</div></div>`).join('');
    $('#plan-body').innerHTML = `
      ${plan.summary ? `<div class="summary">${ic('info')}<span>${esc(plan.summary)}</span></div>` : ''}
      ${plan.project ? `<div class="review-count">Project: <b>${esc(plan.project)}</b></div>` : ''}
      ${stack ? `<div class="hs-t" style="margin:14px 0 6px">Proposed technology stack</div>
        <div class="tbl-wrap"><table class="ptbl"><thead><tr><th>Layer</th><th>Choice</th><th>Rationale</th></tr></thead><tbody>${stack}</tbody></table></div>` : ''}
      ${plan.architecture ? `<div class="hs-t" style="margin:16px 0 6px">Architecture</div><div class="rat" style="white-space:pre-wrap">${esc(plan.architecture)}</div>` : ''}
      ${dgs ? `<div class="hs-t" style="margin:16px 0 8px">${(plan.diagrams || []).length} diagram(s) in the proposal</div>${dgs}` : ''}
      <details class="spec-edit"><summary>${ic('chevron')} Edit plan JSON (advanced)</summary>
        <textarea class="mono" id="plan-json" rows="16" style="margin-top:12px">${esc(JSON.stringify(plan, null, 2))}</textarea>
        <div class="row end" style="margin-top:10px"><button class="btn sm" onclick="App.savePlan()">${ic('check')} Save edits</button></div>
      </details>
      <div class="row" style="margin-top:20px">
        <button class="btn ghost" onclick="App.backToInputs()">${ic('edit')} Edit inputs &amp; re-analyze</button>
        <div class="spacer"></div>
        <button class="btn primary lg" onclick="App.generate()">${ic('play')} Generate proposal (.docx)</button>
      </div>`;
  }
  async function savePlan() {
    try { const p = JSON.parse($('#plan-json').value); await api('PUT', '/api/workspaces/' + current + '/plan', p); planCache = p; toast('Plan saved'); }
    catch (e) { toast('Invalid JSON: ' + e.message, true); }
  }
  async function reopenPlan() {
    const p = planCache || await api('GET', '/api/workspaces/' + current + '/plan');
    await api('PUT', '/api/workspaces/' + current + '/plan', p); histView = false; selVer = null; await refresh();
  }
  function viewProposalPreview() {
    const versions = detail.versions || [];
    if (!versions.length) return `<div class="card"><div class="card-body"><div class="errbox">${ic('warn')}<span>No proposal produced.</span></div></div></div>`;
    if (selVer == null || !versions.some(v => v.id === selVer)) selVer = detail.current_version ?? versions[versions.length - 1].id;
    const v = verById(selVer);
    const base = `/api/workspaces/${current}/versions/${v.id}/preview/`;
    const dgs = (v.diagrams || []).map(n => `<div class="tile"><div class="imgwrap" onclick="App.zoom('${base}${esc(n)}')"><span class="zoomhint">${ic('zoom')}</span><img src="${base}${esc(n)}" loading="lazy"></div></div>`).join('');
    const back = histView ? `<button class="btn ghost sm" onclick="App.closeHistory()" style="margin-bottom:14px">← Back to ${esc(detail.status)}</button>` : '';
    return `${back}<div class="card">
      <div class="card-head"><div class="hi">${ic('doc2')}</div><div><h3>${histView ? 'Version history' : 'Proposal ready'}</h3><div class="sub">${versions.length} version${versions.length > 1 ? 's' : ''} — download the .docx, review the diagrams, iterate or export.</div></div></div>
      <div class="card-body">
        ${timelineHTML()}
        <div class="docx-hero"><div class="dh-ic">${ic('doc2')}</div>
          <div class="dh-txt"><div class="dh-t">${esc(v.docx)}</div><div class="dh-s">${(v.diagrams || []).length} diagram(s) · SharePoint-compatible</div></div>
          <a class="btn primary lg" href="${base}${esc(v.docx)}" download>${ic('download')} Download .docx</a></div>
        ${v.report ? `<details class="spec-edit"><summary>${ic('chevron')} Run report</summary><div class="log" style="margin-top:10px"><pre>${esc(v.report)}</pre></div></details>` : ''}
        ${dgs ? `<div class="hs-t" style="margin:18px 0 8px">Diagrams in this proposal</div><div class="grid">${dgs}</div>` : ''}
      </div>
      <div class="card-foot">
        <button class="btn ghost" onclick="App.backToInputs()">${ic('edit')} Edit inputs</button>
        <button class="btn" onclick="App.reopenPlan()">${ic('code')} Edit plan &amp; regenerate</button>
        <div class="spacer"></div>
        <button class="btn primary lg" onclick="App.exportZip()">${ic('download')} Export v${selVer} (zip)</button>
      </div>
    </div>`;
  }
  async function backToInputs() {
    histView = false; cmpMode = false;   // leave any history view before showing the inputs screen
    const fd = new FormData();
    fd.append('prompt', detail.prompt || ''); fd.append('folder', detail.folder || '');
    await api('POST', '/api/workspaces/' + current + '/inputs', fd, true);
    await refresh();
  }
  async function generate() {
    try { selVer = null; cmpMode = false; histView = false; await api('POST', '/api/workspaces/' + current + '/generate'); toast('Generating…'); await refresh(); }
    catch (e) { toast(e.message, true); }
  }

  // ---------- PREVIEW (version-aware) ----------
  const FMT_ICON = { svg: 'image', drawio: 'diagram', docx: 'doc2', png: 'image' };
  const verById = (id) => (detail.versions || []).find(v => v.id === id);
  const shortTime = (iso) => { // local MM/DD HH:MM (user's machine timezone)
    try { const d = new Date(iso); if (!isNaN(d)) return d.toLocaleString([], { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e) {}
    return (iso || '').slice(5, 16);
  };

  function tileHTML(v, r) {
    const base = `/api/workspaces/${current}/versions/${v.id}/preview/`;
    if (!r.ok) return `<div class="tile"><div class="bad">✕ ${esc(r.slug)}\n${esc((r.error || '').slice(0, 400))}</div>
      <div class="cap"><div class="t"><span class="tt">${esc(r.title)}</span></div></div></div>`;
    const links = ['png', 'svg', 'drawio', 'docx'].filter(x => r[x] || x === 'png').map(x => {
      const file = x === 'png' ? r.png : r[x];
      return file ? `<a class="fmt" href="${base}${esc(file)}" target="_blank">${ic(FMT_ICON[x])}${x}</a>` : '';
    }).join('');
    return `<div class="tile">
      <div class="imgwrap" onclick="App.zoom('${base}${esc(r.png)}')"><span class="zoomhint">${ic('zoom')}</span><img src="${base}${esc(r.png)}" alt="${esc(r.title)}" loading="lazy"></div>
      <div class="cap"><div class="t"><span class="kindtag">${esc(r.kind)}</span><span class="tt">${esc(r.title)}</span></div>
        <div class="links">${links}</div></div></div>`;
  }
  function checkbarHTML(v) {
    const chk = v.check || { blockers: 0, warnings: 0 }, res = v.results || [];
    const nOk = res.filter(r => r.ok).length;
    const cls = chk.blockers ? 'b' : (chk.warnings ? 'w' : 'g');
    const txt = chk.blockers ? `${chk.blockers} blocker(s)` : (chk.warnings ? `${chk.warnings} warning(s)` : 'All checks passed');
    return `<div class="checkbar"><span class="chk ${cls}"><span class="dot"></span>${txt}</span>
      <span class="chk n"><span class="dot"></span>${nOk}/${res.length} rendered</span></div>`;
  }
  const gridHTML = (v) => `<div class="grid">${(v.results || []).map(r => tileHTML(v, r)).join('')}</div>`;

  function timelineHTML() {
    const vs = (detail.versions || []).slice().sort((a, b) => b.id - a.id);
    const chips = vs.map(v => {
      const chk = v.check || {}, cls = chk.blockers ? 'b' : (chk.warnings ? 'w' : 'g');
      const cur = v.id === detail.current_version, on = v.id === selVer;
      return `<div class="vchip ${on ? 'on' : ''}" onclick="App.viewVersion(${v.id})" title="${esc(v.source || '')}">
        <div class="vt"><span class="vdot ${cls}"></span>v${v.id}${cur ? ' <span class="vnow">latest</span>' : ''}${v.label ? ` · ${esc(v.label)}` : ''}</div>
        <div class="vm">${esc(shortTime(v.created))} · ${esc(v.source || '')}</div></div>`;
    }).join('');
    const cmpBtn = detail.type === 'proposal' ? ''   // compare grid is diagram-specific
      : `<button class="btn sm ${cmpMode ? 'primary' : ''}" onclick="App.toggleCompare()">${ic('grid')} ${cmpMode ? 'Exit compare' : 'Compare'}</button>`;
    return `<div class="vbar"><div class="vscroll">${chips}</div>${cmpBtn}</div>`;
  }
  function verSelect(id, side) {
    const vs = (detail.versions || []).slice().sort((a, b) => b.id - a.id);
    return `<select class="vsel" onchange="App.setCmp('${side}', +this.value)">${vs.map(v =>
      `<option value="${v.id}" ${v.id === id ? 'selected' : ''}>v${v.id} — ${esc(v.source || '')} (${esc(shortTime(v.created))})</option>`).join('')}</select>`;
  }
  function compareHTML() {
    const col = (v, side) => v ? `<div class="cmpcol"><div class="cmphead">${verSelect(v.id, side)}</div>${checkbarHTML(v)}${gridHTML(v)}</div>` : '';
    return `<div class="cmpwrap">${col(verById(cmpA), 'a')}${col(verById(cmpB), 'b')}</div>`;
  }

  function viewPreview() {
    const versions = detail.versions || [];
    if (!versions.length) return `<div class="card"><div class="card-body"><div class="errbox">${ic('warn')}<span>No render produced.</span></div></div></div>`;
    if (selVer == null || !versions.some(v => v.id === selVer)) selVer = detail.current_version ?? versions[versions.length - 1].id;
    if (cmpA == null || !versions.some(v => v.id === cmpA)) cmpA = detail.current_version;
    if (cmpB == null || !versions.some(v => v.id === cmpB)) { const o = versions.filter(v => v.id !== cmpA); cmpB = (o[o.length - 1] || versions[0]).id; }

    const v = verById(selVer);
    const body = cmpMode ? compareHTML() : (checkbarHTML(v) + gridHTML(v));
    const foot = cmpMode
      ? `<div class="spacer"></div><button class="btn" onclick="App.toggleCompare()">Done comparing</button>`
      : `<button class="btn ghost" onclick="App.backToInputs()">${ic('edit')} Edit inputs</button>
         <button class="btn" onclick="App.iterateFrom(${selVer})">${ic('code')} Iterate from v${selVer}</button>
         <div class="spacer"></div>
         <button class="btn primary lg" onclick="App.exportZip()">${ic('download')} Export v${selVer}</button>`;
    const sub = versions.length > 1
      ? `${versions.length} versions — click one to view, or Compare two.`
      : 'Review the render, iterate if needed, then export.';
    const back = histView ? `<button class="btn ghost sm" onclick="App.closeHistory()" style="margin-bottom:14px">← Back to ${esc(detail.status)}</button>` : '';
    return `${back}<div class="card">
      <div class="card-head"><div class="hi">${ic('grid')}</div><div><h3>${histView ? 'Version history' : 'Preview &amp; export'}</h3><div class="sub">${sub}</div></div></div>
      <div class="card-body">${timelineHTML()}${body}</div>
      <div class="card-foot">${foot}</div>
    </div>`;
  }
  function viewHistoryStrip() {
    const vs = (detail.versions || []).slice().sort((a, b) => b.id - a.id);
    const chips = vs.map(v => {
      const chk = v.check || {}, cls = chk.blockers ? 'b' : (chk.warnings ? 'w' : 'g');
      const cur = v.id === detail.current_version;
      return `<div class="vchip" onclick="App.openHistory(${v.id})" title="${esc(v.source || '')}">
        <div class="vt"><span class="vdot ${cls}"></span>v${v.id}${cur ? ' <span class="vnow">latest</span>' : ''}</div>
        <div class="vm">${esc(shortTime(v.created))} · ${esc(v.source || '')}</div></div>`;
    }).join('');
    return `<div class="card" style="margin-top:18px">
      <div class="card-head"><div class="hi">${ic('grid')}</div><div><h3>Version history</h3>
        <div class="sub">${vs.length} generated version${vs.length > 1 ? 's' : ''} — click one to view, compare, or export.</div></div></div>
      <div class="card-body"><div class="vscroll">${chips}</div></div></div>`;
  }
  function openHistory(id) { histView = true; selVer = id; cmpMode = false; render(); }
  function closeHistory() { histView = false; cmpMode = false; render(); }
  function viewVersion(id) { selVer = id; cmpMode = false; render(); }
  function toggleCompare() { cmpMode = !cmpMode; render(); }
  function setCmp(side, id) { if (side === 'a') cmpA = id; else cmpB = id; render(); }
  async function iterateFrom(id) {
    try {
      await api('POST', `/api/workspaces/${current}/versions/${id}/restore`);
      selVer = null; histView = false; cmpMode = false;   // leave the history view -> show the review gate
      toast(`Editing from v${id} — tweak the spec, then Generate`);
      await refresh();
    } catch (e) { toast(e.message, true); }
  }
  function exportZip() { window.location = `/api/workspaces/${current}/export?version=${selVer}`; }
  function zoom(src) { const lb = el(`<div class="lightbox"><img src="${src}"></div>`); lb.onclick = () => lb.remove(); document.body.appendChild(lb); }

  // ---------- ERROR ----------
  function viewError() {
    const log = (detail.job?.log || []).map(esc).join('\n');
    const retry = detail.job?.phase === 'generate'
      ? `<button class="btn primary" onclick="App.generate()">${ic('play')} Retry generate</button>`
      : `<button class="btn primary" onclick="App.backToInputs()">${ic('edit')} Back to inputs</button>`;
    return `<div class="card"><div class="card-body">
      ${log ? `<div class="log" style="margin:0"><div class="log-head"><span class="tl"><i></i><i></i><i></i></span> job log</div><pre>${log}</pre></div>` : ''}
      </div><div class="card-foot"><div class="spacer"></div>
        <button class="btn ghost" onclick="App.backToInputs()">Edit inputs</button>${retry}</div></div>`;
  }

  async function del() {
    const ok = await modalConfirm({ title: 'Delete workspace?',
      message: `“${detail.name}” and all its versions and output will be permanently removed. This cannot be undone.`,
      okText: 'Delete', danger: true });
    if (!ok) return;
    await api('DELETE', '/api/workspaces/' + current);
    showEmpty();
    await loadList();
  }

  // check the claude CLI is installed + signed in (Refine needs it); warn if not
  let health = null;
  async function checkHealth() {
    const bar = $('#authwarn');
    try { health = await api('GET', '/api/health'); } catch (e) { health = null; return; }
    if (!health.claude_installed) {
      bar.innerHTML = `${ic('warn')}<span>The <code>claude</code> CLI isn’t installed — the <b>Refine</b> step won’t work. Install Claude Code, then reload. (Generate / Preview / Export still work.)</span>`;
      bar.classList.remove('hidden');
    } else if (!health.logged_in) {
      bar.innerHTML = `${ic('warn')}<span>You’re not signed in to <code>claude</code> — <b>Refine</b> will fail. Run <code>claude auth login</code> in a terminal, then reload.</span>`;
      bar.classList.remove('hidden');
    } else {
      bar.classList.add('hidden');
    }
  }

  // restore the selected workspace across F5 / reload via the URL hash (#<id>)
  async function boot() {
    checkHealth();
    await loadList();
    const id = (location.hash || '').slice(1);
    if (id) { try { await select(id); } catch (e) { showEmpty(); await loadList(); } }
  }
  async function onHashChange() {
    const id = (location.hash || '').slice(1);
    if (!id) { if (current) showEmpty(); return; }
    if (id !== current) { try { await select(id); } catch (e) { showEmpty(); await loadList(); } }
  }

  $('#new-ws').onclick = newWorkspace;
  window.addEventListener('hashchange', onHashChange);
  boot();

  return { newWorkspace, saveAndRefine, generate, exportZip, del, zoom, rmFile,
           saveManifest, backToInputs, pickFiles, pickFolder, browseFolder,
           viewVersion, toggleCompare, setCmp, iterateFrom, openHistory, closeHistory, openHelp,
           savePlan, reopenPlan };
})();

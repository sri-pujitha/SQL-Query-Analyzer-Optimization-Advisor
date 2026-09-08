const API_BASE = ""; // same-origin when served by FastAPI; change if hosting separately

function getConnection() {
  return {
    host: document.getElementById("host").value.trim(),
    port: parseInt(document.getElementById("port").value, 10) || 3306,
    user: document.getElementById("user").value.trim(),
    password: document.getElementById("password").value,
    database: document.getElementById("database").value.trim(),
  };
}

document.getElementById("test-conn-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("conn-status");
  statusEl.className = "";
  statusEl.textContent = "Testing…";
  try {
    const res = await fetch(`${API_BASE}/api/connect-test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getConnection()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Connection failed");
    statusEl.textContent = `Connected (MySQL ${data.mysql_version})`;
    statusEl.className = "status-ok";
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status-error";
  }
});

document.getElementById("analyze-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("analyze-status");
  const resultsPanel = document.getElementById("results-panel");
  const query = document.getElementById("query").value.trim();

  if (!query) {
    statusEl.textContent = "Enter a SELECT query first.";
    statusEl.className = "status-error";
    return;
  }

  statusEl.className = "";
  statusEl.textContent = "Analyzing…";
  resultsPanel.hidden = true;

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...getConnection(), query }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Analysis failed");

    statusEl.textContent = "";
    renderTree(data.tree);
    renderFindings(data.findings);
    resultsPanel.hidden = false;
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status-error";
  }
});

function badgeClassFor(node) {
  if (node.access_type === "ALL") return "badge-ALL";
  if (node.access_type === "index") return "badge-index";
  if (node.access_type) return "badge-ok";
  return "badge-default";
}

function renderTree(root) {
  const container = document.getElementById("plan-tree");
  container.innerHTML = "";
  if (!root.children || root.children.length === 0) {
    container.innerHTML = '<p class="empty-state">No plan data returned.</p>';
    return;
  }
  root.children.forEach((child) => container.appendChild(renderNode(child)));
}

function renderNode(node) {
  const el = document.createElement("div");
  el.className = "node";
  if (node.using_filesort) el.classList.add("filesort");
  if (node.using_temporary_table) el.classList.add("tmptable");

  const header = document.createElement("div");
  header.className = "node-header";

  const badge = document.createElement("span");
  badge.className = `node-badge ${badgeClassFor(node)}`;
  badge.textContent = node.access_type || node.node_type;
  header.appendChild(badge);

  const label = document.createElement("strong");
  label.textContent = node.label;
  header.appendChild(label);

  el.appendChild(header);

  const metaParts = [];
  if (node.rows_examined != null) metaParts.push(`~${node.rows_examined} rows/scan`);
  if (node.filtered_percent != null) metaParts.push(`${node.filtered_percent.toFixed(1)}% filtered`);
  if (node.key) metaParts.push(`key: ${node.key}`);
  if (!node.key && node.possible_keys && node.possible_keys.length) {
    metaParts.push(`unused candidate keys: ${node.possible_keys.join(", ")}`);
  }
  if (node.using_filesort) metaParts.push("uses filesort");
  if (node.using_temporary_table) metaParts.push("uses temp table");

  if (metaParts.length) {
    const meta = document.createElement("div");
    meta.className = "node-meta";
    meta.textContent = metaParts.join(" · ");
    el.appendChild(meta);
  }

  (node.children || []).forEach((child) => el.appendChild(renderNode(child)));

  return el;
}

function renderFindings(findings) {
  const container = document.getElementById("findings-list");
  container.innerHTML = "";

  if (!findings || findings.length === 0) {
    container.innerHTML = '<p class="empty-state">No issues detected — plan looks healthy.</p>';
    return;
  }

  findings.forEach((f) => {
    const el = document.createElement("div");
    el.className = `finding sev-${f.severity}`;

    const title = document.createElement("div");
    title.className = "finding-title";
    title.textContent = `[${f.severity.toUpperCase()}] ${f.title}`;
    el.appendChild(title);

    const detail = document.createElement("div");
    detail.className = "finding-detail";
    detail.textContent = f.detail;
    el.appendChild(detail);

    const suggestion = document.createElement("div");
    suggestion.className = "finding-suggestion";
    suggestion.textContent = f.suggestion;
    el.appendChild(suggestion);

    container.appendChild(el);
  });
}

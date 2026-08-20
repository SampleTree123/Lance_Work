const DECISION_LABELS = {
  unreviewed: "未审查",
  accepted: "接受",
  rejected: "淘汰",
  deferred: "暂缓",
};

const SEMANTIC_OPTIONS = [
  ["", "未标注"],
  ["idle", "待机"],
  ["locomotion", "移动"],
  ["gesture", "手势"],
  ["exercise", "运动"],
  ["transition", "过渡"],
  ["interaction", "交互"],
  ["other", "其他"],
];

const PRESENTATION_OPTIONS = [
  ["", "未标注"],
  ["female", "偏女性"],
  ["male", "偏男性"],
  ["unisex", "通用"],
  ["unsure", "不确定"],
];

const PROP_OPTIONS = [
  ["", "未标注"],
  ["none", "无道具"],
  ["one_hand", "单手道具"],
  ["two_hand", "双手道具"],
  ["furniture", "家具/支撑物"],
  ["partner", "另一人物"],
  ["unknown", "疑似依赖"],
];

let activeWorkspaceController = null;

export function disposeReviewWorkspace() {
  activeWorkspaceController?.abort();
  activeWorkspaceController = null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function selectOptions(options, selected) {
  return options
    .map(([value, label]) => `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
}

function flattenCandidates(run) {
  const candidates = [];
  for (const [groupId, group] of Object.entries(run.groups ?? {})) {
    for (const item of group.cases ?? []) {
      candidates.push({
        ...item,
        groupId,
        groupLabel: group.label ?? groupId,
        overview: group.overview ?? null,
      });
    }
  }
  return candidates;
}

function emptyItem() {
  return {
    decision: "unreviewed",
    naturalness: null,
    semantic_class: "",
    presentation: "",
    prop_dependency: "",
    notes: "",
  };
}

function normalizeItem(value) {
  const item = { ...emptyItem(), ...(value ?? {}) };
  if (!(item.decision in DECISION_LABELS)) item.decision = "unreviewed";
  const score = Number(item.naturalness);
  item.naturalness = Number.isInteger(score) && score >= 1 && score <= 5 ? score : null;
  for (const key of ["semantic_class", "presentation", "prop_dependency", "notes"]) {
    item[key] = String(item[key] ?? "");
  }
  return item;
}

function storageKey(run) {
  const reviewId = run.review?.review_id ?? run.id;
  return `lance-visual-review:${reviewId}:v1`;
}

function newState(run, candidates) {
  return {
    schema_version: 1,
    review_id: run.review?.review_id ?? run.id,
    run_id: run.id,
    source_fingerprint: run.review?.source_fingerprint ?? null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    items: Object.fromEntries(candidates.map((item) => [item.id, emptyItem()])),
  };
}

function loadState(run, candidates) {
  const fallback = newState(run, candidates);
  try {
    const raw = localStorage.getItem(storageKey(run));
    if (!raw) return { state: fallback, restored: false, warning: null };
    const parsed = JSON.parse(raw);
    if (parsed?.schema_version !== 1 || parsed?.run_id !== run.id) {
      return { state: fallback, restored: false, warning: "已有本地记录与当前批次不匹配，未自动载入。" };
    }
    if ((parsed.source_fingerprint ?? null) !== (fallback.source_fingerprint ?? null)) {
      return { state: fallback, restored: false, warning: "候选来源已变化，旧记录未自动合并。" };
    }
    const items = {};
    for (const candidate of candidates) {
      items[candidate.id] = normalizeItem(parsed.items?.[candidate.id]);
    }
    return {
      state: { ...fallback, ...parsed, items, updated_at: parsed.updated_at ?? fallback.updated_at },
      restored: true,
      warning: null,
    };
  } catch (error) {
    return { state: fallback, restored: false, warning: `本地记录读取失败：${error.message}` };
  }
}

function saveState(run, state) {
  state.updated_at = new Date().toISOString();
  try {
    localStorage.setItem(storageKey(run), JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

function decisionCounts(candidates, state) {
  const counts = { unreviewed: 0, accepted: 0, rejected: 0, deferred: 0 };
  for (const candidate of candidates) {
    const decision = state.items[candidate.id]?.decision ?? "unreviewed";
    counts[decision] = (counts[decision] ?? 0) + 1;
  }
  return counts;
}

function candidateSearchText(candidate) {
  return [
    candidate.id,
    candidate.label,
    candidate.groupLabel,
    ...Object.entries(candidate.parameters ?? {}).flatMap(([key, value]) => [key, value]),
  ].join(" ").toLocaleLowerCase("zh-CN");
}

function candidateImages(candidate, order = []) {
  const images = candidate.images ?? {};
  const keys = [
    ...order.filter((key) => images[key]),
    ...Object.keys(images).filter((key) => !order.includes(key)),
  ];
  return keys.map((key) => [key, images[key]]);
}

function metadataRows(candidate) {
  const labels = {
    source_package: "来源包",
    source_format: "格式",
    motion_length_frames: "帧长",
    root_motion_class: "Root 分类",
    facial_channel_class: "面部通道",
    review_family: "机器语义",
    hidden_dependency_count: "隐藏依赖",
  };
  const preferred = Object.keys(labels);
  const entries = Object.entries(candidate.parameters ?? {});
  entries.sort(([a], [b]) => {
    const ai = preferred.indexOf(a);
    const bi = preferred.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
  return entries
    .map(([key, value]) => `
      <div class="review-meta__item" title="${escapeHtml(value)}">
        <span>${escapeHtml(labels[key] ?? key)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>`)
    .join("");
}

function downloadJson(run, candidates, state) {
  const counts = decisionCounts(candidates, state);
  const payload = {
    ...state,
    exported_at: new Date().toISOString(),
    candidate_count: candidates.length,
    counts,
    items: Object.fromEntries(candidates.map((candidate) => [candidate.id, {
      candidate_id: candidate.id,
      label: candidate.label,
      group_id: candidate.groupId,
      ...normalizeItem(state.items[candidate.id]),
    }])),
  };
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = run.review?.export_filename ?? `${run.id}-review-decisions.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function naturalnessButtons(value) {
  return [1, 2, 3, 4, 5]
    .map((score) => `<button type="button" data-score="${score}" aria-pressed="${value === score}">${score}</button>`)
    .join("");
}

function decisionButtons(value) {
  return ["accepted", "rejected", "deferred", "unreviewed"]
    .map((decision) => `<button type="button" class="review-decision__${decision}" data-decision="${decision}" aria-pressed="${value === decision}">${DECISION_LABELS[decision]}</button>`)
    .join("");
}

function candidateRow(candidate, item, active) {
  const score = item.naturalness ? ` · ${item.naturalness}/5` : "";
  return `
    <button type="button" class="review-candidate ${active ? "review-candidate--active" : ""}" data-candidate-id="${escapeHtml(candidate.id)}" aria-current="${active}" title="${escapeHtml(`${candidate.label} | ${candidate.groupLabel}`)}">
      <span class="review-candidate__state review-candidate__state--${escapeHtml(item.decision)}" aria-hidden="true"></span>
      <span class="review-candidate__body">
        <strong>${escapeHtml(candidate.label)}</strong>
        <small>${escapeHtml(candidate.groupLabel)}</small>
      </span>
      <span class="review-candidate__decision">${escapeHtml(DECISION_LABELS[item.decision])}${score}</span>
    </button>`;
}

export function renderReviewWorkspace(run, helpers) {
  disposeReviewWorkspace();
  activeWorkspaceController = new AbortController();
  const workspaceSignal = activeWorkspaceController.signal;
  const { app, navigateHome, openImage, formatDate, statusPill, metricStrip, artifactList } = helpers;
  const candidates = flattenCandidates(run);
  if (!candidates.length) throw new Error("候选审查批次没有可显示的动作。");

  const loaded = loadState(run, candidates);
  const state = loaded.state;
  let activeId = candidates[0].id;
  let activeImageKey = null;
  let filterDecision = "all";
  let searchText = "";

  app.innerHTML = `
    <article class="run-page review-run">
      <div class="run-topline">
        <button class="back-button" id="runBack" type="button">← 返回全部结果</button>
        ${statusPill(run.status)}
      </div>
      <header class="run-heading review-heading">
        <div>
          <span class="run-row__task">${escapeHtml(run.task)}</span>
          <h1>${escapeHtml(run.title)}</h1>
          <p>${escapeHtml(run.summary)}</p>
        </div>
        <div class="run-heading__meta">
          <span class="tag">${escapeHtml(formatDate(run.created_at, true))}</span>
          ${(run.tags ?? []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
        </div>
      </header>
      <section class="metric-strip" aria-label="结果统计">${metricStrip(run.metrics)}</section>
      <section class="review-progress" aria-label="审查进度">
        <div class="review-progress__bar"><span id="reviewProgressBar"></span></div>
        <div class="review-progress__counts" id="reviewProgressCounts"></div>
        <output id="reviewSaveStatus" class="review-save-status" aria-live="polite"></output>
      </section>
      <section class="review-toolbar" aria-label="审查工具">
        <div class="field review-toolbar__search">
          <label for="reviewSearch">搜索候选</label>
          <input id="reviewSearch" type="search" placeholder="动作名、来源包或语义">
        </div>
        <div class="field">
          <label for="reviewFilter">审查状态</label>
          <select id="reviewFilter">
            <option value="all">全部候选</option>
            <option value="unreviewed">未审查</option>
            <option value="accepted">已接受</option>
            <option value="rejected">已淘汰</option>
            <option value="deferred">已暂缓</option>
          </select>
        </div>
        <div class="review-toolbar__actions">
          <button class="plain-button" id="reviewImport" type="button">导入决定</button>
          <button class="plain-button plain-button--primary" id="reviewExport" type="button">导出决定</button>
          <input id="reviewImportFile" type="file" accept="application/json,.json" hidden>
        </div>
      </section>
      ${loaded.warning ? `<p class="review-warning" role="status">${escapeHtml(loaded.warning)}</p>` : ""}
      <section class="review-workspace">
        <aside class="review-queue" aria-label="候选动作">
          <div class="review-queue__heading"><strong id="reviewVisibleCount"></strong><span>当前列表</span></div>
          <div class="review-queue__list" id="reviewQueue"></div>
        </aside>
        <div class="review-detail" id="reviewDetail"></div>
      </section>
      <section class="review-artifacts">
        <div class="section-heading"><div><h2>原始产物</h2><p>候选清单、动态证据和来源记录。</p></div></div>
        <div class="artifact-list">${artifactList(run.artifacts)}</div>
      </section>
    </article>`;

  const queue = app.querySelector("#reviewQueue");
  const detail = app.querySelector("#reviewDetail");
  const search = app.querySelector("#reviewSearch");
  const filter = app.querySelector("#reviewFilter");
  const saveStatus = app.querySelector("#reviewSaveStatus");
  const importFile = app.querySelector("#reviewImportFile");

  function persist(message = "已保存在此浏览器") {
    const saved = saveState(run, state);
    saveStatus.textContent = saved ? `${message} · ${new Date().toLocaleTimeString("zh-CN", { hour12: false })}` : "本地保存失败，请立即导出 JSON";
    saveStatus.classList.toggle("review-save-status--error", !saved);
    updateProgress();
  }

  function filteredCandidates() {
    const needle = searchText.toLocaleLowerCase("zh-CN");
    return candidates.filter((candidate) => {
      const item = state.items[candidate.id];
      return (filterDecision === "all" || item.decision === filterDecision)
        && (!needle || candidateSearchText(candidate).includes(needle));
    });
  }

  function updateProgress() {
    const counts = decisionCounts(candidates, state);
    const completed = candidates.length - counts.unreviewed;
    const percent = candidates.length ? (completed / candidates.length) * 100 : 0;
    app.querySelector("#reviewProgressBar").style.width = `${percent}%`;
    app.querySelector("#reviewProgressCounts").innerHTML = `
      <strong>${completed}/${candidates.length}</strong>
      <span>接受 ${counts.accepted}</span>
      <span>淘汰 ${counts.rejected}</span>
      <span>暂缓 ${counts.deferred}</span>
      <span>未审 ${counts.unreviewed}</span>`;
  }

  function renderQueue() {
    const visible = filteredCandidates();
    app.querySelector("#reviewVisibleCount").textContent = `${visible.length} 个动作`;
    if (!visible.some((candidate) => candidate.id === activeId)) {
      activeId = visible[0]?.id ?? candidates[0].id;
      activeImageKey = null;
    }
    queue.innerHTML = visible.length
      ? visible.map((candidate) => candidateRow(candidate, state.items[candidate.id], candidate.id === activeId)).join("")
      : `<div class="review-queue__empty">当前筛选没有候选</div>`;
    queue.querySelectorAll("[data-candidate-id]").forEach((button) => {
      button.addEventListener("click", () => {
        activeId = button.dataset.candidateId;
        activeImageKey = null;
        renderQueue();
        renderDetail();
      });
    });
    queue.querySelector(`[data-candidate-id="${CSS.escape(activeId)}"]`)?.scrollIntoView({ block: "nearest" });
  }

  function renderDetail() {
    const candidate = candidates.find((item) => item.id === activeId) ?? candidates[0];
    const item = state.items[candidate.id];
    const images = candidateImages(candidate, run.review?.image_order ?? []);
    if (!images.some(([key]) => key === activeImageKey)) activeImageKey = images[0]?.[0] ?? null;
    const activeImage = images.find(([key]) => key === activeImageKey)?.[1] ?? "";
    const visible = filteredCandidates();
    const visibleIndex = visible.findIndex((entry) => entry.id === candidate.id);
    detail.innerHTML = `
      <div class="review-detail__heading">
        <div>
          <span>${escapeHtml(candidate.groupLabel)}</span>
          <h2>${escapeHtml(candidate.label)}</h2>
          <code>${escapeHtml(candidate.id)}</code>
        </div>
        <div class="review-detail__nav">
          <button class="icon-button" id="reviewPrev" type="button" aria-label="上一个动作" title="上一个动作" ${visibleIndex <= 0 ? "disabled" : ""}>←</button>
          <output>${visibleIndex >= 0 ? `${visibleIndex + 1}/${visible.length}` : "—"}</output>
          <button class="icon-button" id="reviewNext" type="button" aria-label="下一个动作" title="下一个动作" ${visibleIndex < 0 || visibleIndex >= visible.length - 1 ? "disabled" : ""}>→</button>
        </div>
      </div>
      <div class="review-media">
        <button type="button" class="review-media__main" id="reviewMainImage" aria-label="打开当前关键帧大图">
          <img src="${escapeHtml(activeImage)}" alt="${escapeHtml(candidate.label)} ${escapeHtml(activeImageKey)}">
        </button>
        <div class="review-timeline" aria-label="动作关键帧">
          ${images.map(([key, url]) => `
            <button type="button" data-image-key="${escapeHtml(key)}" aria-pressed="${key === activeImageKey}" title="${escapeHtml(key)}">
              <img src="${escapeHtml(url)}" alt="" loading="lazy">
              <span>${escapeHtml(key)}</span>
            </button>`).join("")}
        </div>
      </div>
      <div class="review-meta">${metadataRows(candidate)}</div>
      <form class="review-form" id="reviewForm">
        <fieldset class="review-fieldset review-fieldset--decision">
          <legend>审查决定</legend>
          <div class="review-decision">${decisionButtons(item.decision)}</div>
        </fieldset>
        <fieldset class="review-fieldset">
          <legend>自然度</legend>
          <div class="review-score" id="reviewScore">${naturalnessButtons(item.naturalness)}</div>
        </fieldset>
        <div class="review-form__grid">
          <div class="field"><label for="semanticClass">动作语义</label><select id="semanticClass">${selectOptions(SEMANTIC_OPTIONS, item.semantic_class)}</select></div>
          <div class="field"><label for="presentation">性别倾向</label><select id="presentation">${selectOptions(PRESENTATION_OPTIONS, item.presentation)}</select></div>
          <div class="field"><label for="propDependency">道具依赖</label><select id="propDependency">${selectOptions(PROP_OPTIONS, item.prop_dependency)}</select></div>
        </div>
        <div class="field review-notes"><label for="reviewNotes">备注</label><textarea id="reviewNotes" rows="4" placeholder="记录不自然、接触错误、适用情境或淘汰原因">${escapeHtml(item.notes)}</textarea></div>
      </form>`;

    detail.querySelectorAll("[data-image-key]").forEach((button) => {
      button.addEventListener("click", () => {
        activeImageKey = button.dataset.imageKey;
        renderDetail();
      });
    });
    detail.querySelector("#reviewMainImage")?.addEventListener("click", () => openImage(activeImage, `${candidate.label} · ${activeImageKey}`));
    detail.querySelectorAll("[data-decision]").forEach((button) => {
      button.addEventListener("click", () => {
        item.decision = button.dataset.decision;
        persist();
        renderQueue();
        renderDetail();
      });
    });
    detail.querySelectorAll("[data-score]").forEach((button) => {
      button.addEventListener("click", () => {
        item.naturalness = Number(button.dataset.score);
        persist();
        renderQueue();
        renderDetail();
      });
    });
    for (const [selector, key] of [["#semanticClass", "semantic_class"], ["#presentation", "presentation"], ["#propDependency", "prop_dependency"]]) {
      detail.querySelector(selector).addEventListener("change", (event) => {
        item[key] = event.target.value;
        persist();
      });
    }
    detail.querySelector("#reviewNotes").addEventListener("input", (event) => {
      item.notes = event.target.value;
      persist("备注已保存");
    });
    detail.querySelector("#reviewPrev")?.addEventListener("click", () => navigateRelative(-1));
    detail.querySelector("#reviewNext")?.addEventListener("click", () => navigateRelative(1));
  }

  function navigateRelative(offset) {
    const visible = filteredCandidates();
    const index = visible.findIndex((candidate) => candidate.id === activeId);
    const next = visible[index + offset];
    if (!next) return;
    activeId = next.id;
    activeImageKey = null;
    renderQueue();
    renderDetail();
  }

  function applyImportedState(imported) {
    if (imported?.schema_version !== 1 || imported?.run_id !== run.id) {
      throw new Error("该 JSON 不属于当前审查批次。");
    }
    if ((imported.source_fingerprint ?? null) !== (state.source_fingerprint ?? null)) {
      throw new Error("该 JSON 的候选来源指纹与当前批次不同。");
    }
    for (const candidate of candidates) {
      if (imported.items?.[candidate.id]) state.items[candidate.id] = normalizeItem(imported.items[candidate.id]);
    }
    persist("导入内容已合并");
    renderQueue();
    renderDetail();
  }

  app.querySelector("#runBack").addEventListener("click", navigateHome);
  search.addEventListener("input", () => {
    searchText = search.value.trim();
    renderQueue();
    renderDetail();
  });
  filter.addEventListener("change", () => {
    filterDecision = filter.value;
    renderQueue();
    renderDetail();
  });
  app.querySelector("#reviewExport").addEventListener("click", () => downloadJson(run, candidates, state));
  app.querySelector("#reviewImport").addEventListener("click", () => importFile.click());
  importFile.addEventListener("change", async () => {
    const file = importFile.files?.[0];
    if (!file) return;
    try {
      applyImportedState(JSON.parse(await file.text()));
    } catch (error) {
      saveStatus.textContent = `导入失败：${error.message}`;
      saveStatus.classList.add("review-save-status--error");
    } finally {
      importFile.value = "";
    }
  });
  document.addEventListener("keydown", (event) => {
    if (!app.contains(document.activeElement)) return;
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if (event.key === "ArrowLeft") navigateRelative(-1);
    if (event.key === "ArrowRight") navigateRelative(1);
  }, { signal: workspaceSignal });

  updateProgress();
  renderQueue();
  renderDetail();
  saveStatus.textContent = loaded.restored ? "已恢复此浏览器中的审查进度" : "尚未产生本地修改";
  app.focus({ preventScroll: true });
}

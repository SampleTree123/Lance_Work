import { disposeReviewWorkspace, renderReviewWorkspace } from "./review-workspace.js?v=20260818c";

const app = document.querySelector("#app");
const registryStatus = document.querySelector("#registryStatus");
const homeButton = document.querySelector("#homeButton");
const imageDialog = document.querySelector("#imageDialog");
const dialogImage = document.querySelector("#dialogImage");
const dialogCaption = document.querySelector("#dialogCaption");
const dialogClose = document.querySelector("#dialogClose");
const dialogCanvas = document.querySelector("#dialogCanvas");
const dialogStage = document.querySelector("#dialogStage");
const dialogZoomOut = document.querySelector("#dialogZoomOut");
const dialogZoomIn = document.querySelector("#dialogZoomIn");
const dialogZoomFit = document.querySelector("#dialogZoomFit");
const dialogZoomValue = document.querySelector("#dialogZoomValue");

const STATUS_LABELS = {
  iteration_needed: "需要扩大范围",
  pending_review: "等待审查",
  approved: "已通过",
  complete: "已完成",
  failed: "失败",
  blocked: "已阻塞",
};

const VIEW_LABELS = {
  overview: "总览",
  front: "正面",
  three_quarter: "三分之四",
  profile: "侧面",
  front_three_quarter: "正面四分之三",
  left_profile: "左侧面",
  rear: "背面",
  right_profile: "右侧面",
  post_pose_neutral_front: "中性恢复",
  blink_bilateral_front: "双眼闭合",
  smile_subtle_front: "轻微微笑",
  smile_medium_front: "中等微笑",
  smile_broad_front: "大幅微笑",
  jaw_open_front: "张嘴",
};

const PARAM_LABELS = {
  asset_count: "服装资产数",
  head_width: "Head Width",
  head_depth: "Head Depth",
  skull_height: "Skull Height",
  skull_width: "Skull Width",
  skull_depth: "Skull Depth",
  skull_back_depth: "Skull Back Depth",
  skull_peak: "Skull Peak",
};

let registry = null;
const runCache = new Map();

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusLabel(status) {
  return STATUS_LABELS[status] ?? status ?? "未知状态";
}

function statusPill(status) {
  const safeStatus = /^[a-z_]+$/.test(status ?? "") ? status : "pending_review";
  return `<span class="status-pill status-pill--${safeStatus}">${escapeHtml(statusLabel(status))}</span>`;
}

function formatDate(value, includeTime = false) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value ?? "日期未知";
  }
  const options = includeTime
    ? { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }
    : { year: "numeric", month: "2-digit", day: "2-digit" };
  return new Intl.DateTimeFormat("zh-CN", options).format(parsed);
}

function dateKey(value) {
  return String(value ?? "").slice(0, 10) || "unknown";
}

function navigateHome() {
  if (location.hash === "#/" || location.hash === "") {
    renderHome();
    return;
  }
  location.hash = "#/";
}

function navigateRun(id) {
  location.hash = `#/runs/${encodeURIComponent(id)}`;
}

function showLoading(message = "正在加载可视化结果...") {
  app.innerHTML = `
    <section class="loading-state" aria-live="polite">
      <span class="loading-state__bar" aria-hidden="true"></span>
      <p>${escapeHtml(message)}</p>
    </section>`;
}

function showError(title, detail) {
  app.innerHTML = `
    <section class="error-state" role="alert">
      <div>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(detail)}</p>
        <button class="plain-button" id="errorHome" type="button">返回结果主页</button>
      </div>
    </section>`;
  document.querySelector("#errorHome")?.addEventListener("click", navigateHome);
}

function runMetricsSummary(run) {
  const metrics = Array.isArray(run.metrics) ? run.metrics.slice(0, 3) : [];
  if (!metrics.length) {
    return `<div class="metric-line"><span>记录</span><strong>已登记</strong></div>`;
  }
  return metrics
    .map((metric) => `<div class="metric-line"><span>${escapeHtml(metric.label)}</span><strong>${escapeHtml(metric.value)}</strong></div>`)
    .join("");
}

function runRow(run) {
  return `
    <button class="run-row" type="button" data-run-id="${escapeHtml(run.id)}" aria-label="打开 ${escapeHtml(run.title)}">
      <span class="run-row__thumb">
        <img src="${escapeHtml(run.thumbnail)}" alt="" loading="lazy">
      </span>
      <span class="run-row__main">
        <span class="run-row__task">${escapeHtml(run.task)}</span>
        <h2>${escapeHtml(run.title)}</h2>
        <p>${escapeHtml(run.summary)}</p>
      </span>
      <span class="run-row__meta">${runMetricsSummary(run)}</span>
      <span class="run-row__action">
        ${statusPill(run.status)}
        <span class="open-label">打开结果 →</span>
      </span>
    </button>`;
}

function renderRunGroups(runs, target) {
  if (!runs.length) {
    target.innerHTML = `
      <section class="empty-state">
        <div>
          <h2>没有匹配的结果</h2>
          <p>调整日期、任务、状态或搜索关键词。</p>
        </div>
      </section>`;
    return;
  }

  const grouped = new Map();
  for (const run of runs) {
    const key = dateKey(run.created_at);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(run);
  }

  target.innerHTML = [...grouped.entries()]
    .map(([date, dateRuns]) => `
      <section class="date-group">
        <h2 class="date-group__heading">${escapeHtml(formatDate(date))} · ${dateRuns.length} 个结果分支</h2>
        <div class="run-list">${dateRuns.map(runRow).join("")}</div>
      </section>`)
    .join("");

  target.querySelectorAll("[data-run-id]").forEach((button) => {
    button.addEventListener("click", () => navigateRun(button.dataset.runId));
  });
}

function renderHome() {
  disposeReviewWorkspace();
  if (!registry) return;
  document.title = "Lance Visual Review";
  const runs = [...registry.runs];
  const tasks = [...new Set(runs.map((run) => run.task))].sort((a, b) => a.localeCompare(b, "zh-CN"));
  const statuses = [...new Set(runs.map((run) => run.status))];
  const dates = [...new Set(runs.map((run) => dateKey(run.created_at)))].sort().reverse();

  app.innerHTML = `
    <section class="page-heading">
      <div>
        <h1>可视化结果</h1>
        <p>每次实验作为独立结果分支保留。可按日期和任务回看，进入分支后进行视角切换、A/B 对比和参数审查。</p>
      </div>
      <div class="summary-count"><strong id="visibleCount">${runs.length}</strong><span>个结果分支</span></div>
    </section>

    <section class="filter-band" aria-label="结果筛选">
      <div class="field">
        <label for="searchFilter">搜索</label>
        <input id="searchFilter" type="search" placeholder="任务、标题、标签或结论">
      </div>
      <div class="field">
        <label for="dateFilter">日期</label>
        <select id="dateFilter">
          <option value="">全部日期</option>
          ${dates.map((date) => `<option value="${escapeHtml(date)}">${escapeHtml(formatDate(date))}</option>`).join("")}
        </select>
      </div>
      <div class="field">
        <label for="taskFilter">任务</label>
        <select id="taskFilter">
          <option value="">全部任务</option>
          ${tasks.map((task) => `<option value="${escapeHtml(task)}">${escapeHtml(task)}</option>`).join("")}
        </select>
      </div>
      <div class="field">
        <label for="statusFilter">状态</label>
        <select id="statusFilter">
          <option value="">全部状态</option>
          ${statuses.map((status) => `<option value="${escapeHtml(status)}">${escapeHtml(statusLabel(status))}</option>`).join("")}
        </select>
      </div>
    </section>
    <section id="runGroups" class="run-groups" aria-live="polite"></section>`;

  const target = document.querySelector("#runGroups");
  const visibleCount = document.querySelector("#visibleCount");
  const search = document.querySelector("#searchFilter");
  const date = document.querySelector("#dateFilter");
  const task = document.querySelector("#taskFilter");
  const status = document.querySelector("#statusFilter");

  function applyFilters() {
    const needle = search.value.trim().toLocaleLowerCase("zh-CN");
    const filtered = runs.filter((run) => {
      const searchable = [run.title, run.task, run.summary, ...(run.tags ?? [])].join(" ").toLocaleLowerCase("zh-CN");
      return (!needle || searchable.includes(needle))
        && (!date.value || dateKey(run.created_at) === date.value)
        && (!task.value || run.task === task.value)
        && (!status.value || run.status === status.value);
    });
    visibleCount.textContent = String(filtered.length);
    renderRunGroups(filtered, target);
  }

  search.addEventListener("input", applyFilters);
  date.addEventListener("change", applyFilters);
  task.addEventListener("change", applyFilters);
  status.addEventListener("change", applyFilters);
  applyFilters();
  app.focus({ preventScroll: true });
}

async function loadRun(entry) {
  if (runCache.has(entry.id)) return runCache.get(entry.id);
  const response = await fetch(entry.run_file, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${entry.run_file}`);
  const run = await response.json();
  runCache.set(entry.id, run);
  return run;
}

function metricStrip(metrics) {
  return (metrics ?? [])
    .map((metric) => `<div class="metric"><span>${escapeHtml(metric.label)}</span><strong>${escapeHtml(metric.value)}</strong></div>`)
    .join("");
}

function formatSigned(value) {
  const number = Number(value);
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}`;
}

function scannedRange(run, parameterKey) {
  const values = Object.values(run.groups ?? {})
    .flatMap((group) => group.cases ?? [])
    .map((item) => Number(item.parameters?.[parameterKey]))
    .filter((value) => Number.isFinite(value));
  if (!values.length) return null;
  return [Math.min(...values), Math.max(...values)];
}

function safeRangePanel(run) {
  const ranges = run.decision?.approved_single_axis_ranges;
  if (!ranges || typeof ranges !== "object") return "";
  const items = Object.entries(ranges).map(([key, range]) => {
    const minimum = Number(range?.[0]);
    const maximum = Number(range?.[1]);
    const scanned = scannedRange(run, key);
    const narrowed = scanned && (minimum > scanned[0] || maximum < scanned[1]);
    const scannedText = narrowed
      ? `<span>扫描 ${formatSigned(scanned[0])} ~ ${formatSigned(scanned[1])}</span>`
      : `<span>扫描范围已接受</span>`;
    return `
      <div class="safe-range-item ${narrowed ? "safe-range-item--narrowed" : ""}">
        <span>${escapeHtml(PARAM_LABELS[key] ?? key)}</span>
        <strong>${formatSigned(minimum)} ~ ${formatSigned(maximum)}</strong>
        ${scannedText}
      </div>`;
  }).join("");
  return `
    <section class="safe-range-panel" aria-labelledby="safeRangeHeading">
      <div class="safe-range-panel__heading">
        <div>
          <h2 id="safeRangeHeading">批准的单轴范围</h2>
          <p>下方图片保留原始扫描值；生成角色时以这里的批准范围为准。</p>
        </div>
        <span class="safe-range-panel__scope">多轴组合待验证</span>
      </div>
      <div class="safe-range-grid">${items}</div>
    </section>`;
}

function groupButtons(groups, activeGroup) {
  return Object.entries(groups)
    .map(([key, group]) => `<button type="button" data-group="${escapeHtml(key)}" aria-pressed="${key === activeGroup}" title="${escapeHtml(group.label)}">${escapeHtml(group.label)}</button>`)
    .join("");
}

function viewButtons(group, activeView) {
  const views = ["overview", ...Object.keys(group.comparisons ?? {})];
  return views
    .map((view) => `<button type="button" data-sheet-view="${escapeHtml(view)}" aria-pressed="${view === activeView}">${escapeHtml(VIEW_LABELS[view] ?? view)}</button>`)
    .join("");
}

function viewerUrl(group, view) {
  return view === "overview" ? group.overview : group.comparisons?.[view];
}

function profileOptions(cases, selectedId) {
  return cases
    .map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === selectedId ? "selected" : ""}>${escapeHtml(item.id)} · ${escapeHtml(item.label)}</option>`)
    .join("");
}

function commonImageViews(caseA, caseB) {
  const imagesA = caseA?.images ?? {};
  const imagesB = caseB?.images ?? {};
  return Object.keys(imagesA).filter((view) => imagesA[view] && imagesB[view]);
}

function compareViewOptions(views, selectedView) {
  return views
    .map((view) => `<option value="${escapeHtml(view)}" ${view === selectedView ? "selected" : ""}>${escapeHtml(VIEW_LABELS[view] ?? view)}</option>`)
    .join("");
}

function profileTable(group, approvedRanges = null) {
  const parameterKeys = [...new Set(group.cases.flatMap((item) => Object.keys(item.parameters ?? {})))];
  const hasApprovedRanges = approvedRanges && typeof approvedRanges === "object";
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>方案 ID</th>
            <th>说明</th>
            ${hasApprovedRanges ? "<th>区间判定</th>" : ""}
            ${parameterKeys.map((key) => `<th>${escapeHtml(PARAM_LABELS[key] ?? key)}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${group.cases.map((item) => {
            const outside = hasApprovedRanges && parameterKeys.some((key) => {
              const range = approvedRanges[key];
              const value = Number(item.parameters?.[key] ?? 0);
              return Array.isArray(range) && (value < Number(range[0]) || value > Number(range[1]));
            });
            return `
            <tr class="${outside ? "data-table__row--outside" : ""}">
              <td>${escapeHtml(item.id)}</td>
              <td>${escapeHtml(item.label)}</td>
              ${hasApprovedRanges ? `<td><span class="range-status ${outside ? "range-status--outside" : "range-status--inside"}">${outside ? "扫描证据，超出批准范围" : "批准范围内"}</span></td>` : ""}
              ${parameterKeys.map((key) => `<td>${Number(item.parameters?.[key] ?? 0).toFixed(2)}</td>`).join("")}
            </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>`;
}

function artifactList(artifacts) {
  return (artifacts ?? [])
    .map((artifact) => `
      <a class="artifact-link" href="${escapeHtml(artifact.url)}" target="_blank" rel="noopener">
        <strong>${escapeHtml(artifact.label)}</strong>
        <span>${escapeHtml(artifact.url)}</span>
      </a>`)
    .join("");
}

let dialogZoom = 1;
let dialogDrag = null;

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function dialogFitScale() {
  if (!dialogImage.naturalWidth || !dialogImage.naturalHeight) return 1;
  const availableWidth = Math.max(1, dialogCanvas.clientWidth - 24);
  const availableHeight = Math.max(1, dialogCanvas.clientHeight - 24);
  return Math.min(
    availableWidth / dialogImage.naturalWidth,
    availableHeight / dialogImage.naturalHeight,
    1,
  );
}

function setDialogZoom(value, anchor = null) {
  dialogZoom = clamp(value, 0.5, 6);
  dialogZoomValue.textContent = `${Math.round(dialogZoom * 100)}%`;

  if (!dialogImage.naturalWidth || !dialogImage.naturalHeight) return;

  const anchorX = anchor?.x ?? dialogCanvas.clientWidth / 2;
  const anchorY = anchor?.y ?? dialogCanvas.clientHeight / 2;
  const oldWidth = Math.max(1, dialogStage.scrollWidth);
  const oldHeight = Math.max(1, dialogStage.scrollHeight);
  const contentRatioX = (dialogCanvas.scrollLeft + anchorX) / oldWidth;
  const contentRatioY = (dialogCanvas.scrollTop + anchorY) / oldHeight;
  const fitScale = dialogFitScale();
  const imageWidth = Math.max(1, Math.round(dialogImage.naturalWidth * fitScale * dialogZoom));
  const imageHeight = Math.max(1, Math.round(dialogImage.naturalHeight * fitScale * dialogZoom));
  const stageWidth = Math.max(dialogCanvas.clientWidth, imageWidth + 24);
  const stageHeight = Math.max(dialogCanvas.clientHeight, imageHeight + 24);

  dialogImage.style.width = `${imageWidth}px`;
  dialogImage.style.height = `${imageHeight}px`;
  dialogStage.style.width = `${stageWidth}px`;
  dialogStage.style.height = `${stageHeight}px`;
  dialogCanvas.classList.toggle("image-dialog__canvas--zoomed", dialogZoom > 1);

  requestAnimationFrame(() => {
    dialogCanvas.scrollLeft = contentRatioX * dialogStage.scrollWidth - anchorX;
    dialogCanvas.scrollTop = contentRatioY * dialogStage.scrollHeight - anchorY;
  });
}

function openImage(url, caption) {
  dialogImage.alt = caption;
  dialogCaption.textContent = caption;
  dialogZoom = 1;
  dialogZoomValue.textContent = "100%";
  if (!imageDialog.open) imageDialog.showModal();
  dialogImage.src = url;
  requestAnimationFrame(() => setDialogZoom(1));
}

function attachRunInteractions(run, initialGroup) {
  let activeGroup = initialGroup;
  let activeSheetView = "overview";
  let zoom = 1;

  const sheetImage = document.querySelector("#sheetImage");
  const sheetCaption = document.querySelector("#sheetCaption");
  const groupTabs = document.querySelector("#groupTabs");
  const sheetTabs = document.querySelector("#sheetTabs");
  const profileTableTarget = document.querySelector("#profileTableTarget");
  const compareA = document.querySelector("#compareA");
  const compareB = document.querySelector("#compareB");
  const compareView = document.querySelector("#compareView");
  const compareImageA = document.querySelector("#compareImageA");
  const compareImageB = document.querySelector("#compareImageB");
  const compareLabelA = document.querySelector("#compareLabelA");
  const compareLabelB = document.querySelector("#compareLabelB");

  function group() {
    return run.groups[activeGroup];
  }

  function setZoom(value) {
    zoom = Math.max(0.5, Math.min(2.5, value));
    sheetImage.style.transform = `scale(${zoom})`;
    sheetImage.style.maxWidth = zoom > 1 ? "none" : "100%";
    sheetImage.style.maxHeight = zoom > 1 ? "none" : "100%";
  }

  function updateSheet() {
    const url = viewerUrl(group(), activeSheetView);
    sheetImage.src = url;
    sheetImage.alt = `${group().label} ${VIEW_LABELS[activeSheetView] ?? activeSheetView}`;
    sheetCaption.textContent = `${group().label} · ${VIEW_LABELS[activeSheetView] ?? activeSheetView}`;
    sheetTabs.innerHTML = viewButtons(group(), activeSheetView);
    sheetTabs.querySelectorAll("[data-sheet-view]").forEach((button) => {
      button.addEventListener("click", () => {
        activeSheetView = button.dataset.sheetView;
        setZoom(1);
        updateSheet();
      });
    });
  }

  function updateCompare() {
    const caseA = group().cases.find((item) => item.id === compareA.value) ?? group().cases[0];
    const caseB = group().cases.find((item) => item.id === compareB.value) ?? group().cases.at(-1);
    const view = compareView.value;
    const imageA = caseA?.images?.[view];
    const imageB = caseB?.images?.[view];
    if (!imageA || !imageB) {
      compareImageA.removeAttribute("src");
      compareImageB.removeAttribute("src");
      compareImageA.alt = "当前方案没有共同可用的细节视角";
      compareImageB.alt = "当前方案没有共同可用的细节视角";
      return;
    }
    compareImageA.src = imageA;
    compareImageB.src = imageB;
    compareImageA.alt = `${caseA.label} ${VIEW_LABELS[view] ?? view}`;
    compareImageB.alt = `${caseB.label} ${VIEW_LABELS[view] ?? view}`;
    compareLabelA.textContent = `${caseA.id} · ${caseA.label}`;
    compareLabelB.textContent = `${caseB.id} · ${caseB.label}`;
    compareImageA.closest("button").dataset.caption = compareImageA.alt;
    compareImageB.closest("button").dataset.caption = compareImageB.alt;
  }

  function rebuildCompareViews() {
    const caseA = group().cases.find((item) => item.id === compareA.value) ?? group().cases[0];
    const caseB = group().cases.find((item) => item.id === compareB.value) ?? group().cases.at(-1);
    const previousView = compareView.value;
    const views = commonImageViews(caseA, caseB);
    const selectedView = views.includes(previousView) ? previousView : views[0];
    compareView.innerHTML = compareViewOptions(views, selectedView);
    updateCompare();
  }

  function rebuildGroup() {
    const cases = group().cases;
    const selectedA = cases[0]?.id;
    const selectedB = cases.at(-1)?.id;
    activeSheetView = "overview";
    groupTabs.innerHTML = groupButtons(run.groups, activeGroup);
    compareA.innerHTML = profileOptions(cases, selectedA);
    compareB.innerHTML = profileOptions(cases, selectedB);
    profileTableTarget.innerHTML = profileTable(
      group(),
      run.decision?.approved_single_axis_ranges ?? null,
    );
    groupTabs.querySelectorAll("[data-group]").forEach((button) => {
      button.addEventListener("click", () => {
        activeGroup = button.dataset.group;
        setZoom(1);
        rebuildGroup();
      });
    });
    requestAnimationFrame(() => {
      const activeButton = groupTabs.querySelector('[aria-pressed="true"]');
      activeButton?.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
    updateSheet();
    rebuildCompareViews();
  }

  document.querySelector("#runBack").addEventListener("click", navigateHome);
  document.querySelector("#zoomIn").addEventListener("click", () => setZoom(zoom + 0.2));
  document.querySelector("#zoomOut").addEventListener("click", () => setZoom(zoom - 0.2));
  document.querySelector("#zoomFit").addEventListener("click", () => setZoom(1));
  document.querySelector("#openSheet").addEventListener("click", () => openImage(sheetImage.src, sheetImage.alt));
  sheetImage.addEventListener("click", () => openImage(sheetImage.src, sheetImage.alt));
  compareA.addEventListener("change", rebuildCompareViews);
  compareB.addEventListener("change", rebuildCompareViews);
  compareView.addEventListener("change", updateCompare);
  document.querySelectorAll("[data-compare-pane]").forEach((button) => {
    button.addEventListener("click", () => {
      const image = button.querySelector("img");
      openImage(image.src, button.dataset.caption || image.alt);
    });
  });
  groupTabs.addEventListener("wheel", (event) => {
    if (groupTabs.scrollWidth <= groupTabs.clientWidth) return;
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    event.preventDefault();
    groupTabs.scrollLeft += event.deltaY;
  }, { passive: false });
  rebuildGroup();
}

function renderRun(run) {
  disposeReviewWorkspace();
  if (run.review?.mode === "candidate_review") {
    document.title = `${run.title} · Lance Visual Review`;
    renderReviewWorkspace(run, {
      app,
      navigateHome,
      openImage,
      formatDate,
      statusPill,
      metricStrip,
      artifactList,
    });
    return;
  }
  const groupKeys = Object.keys(run.groups ?? {});
  if (!groupKeys.length) {
    showError("结果记录不完整", `${run.id} 没有可显示的分组。`);
    return;
  }
  const initialGroup = groupKeys[0];
  const group = run.groups[initialGroup];
  document.title = `${run.title} · Lance Visual Review`;
  app.innerHTML = `
    <article class="run-page">
      <div class="run-topline">
        <button class="back-button" id="runBack" type="button">← 返回全部结果</button>
        ${statusPill(run.status)}
      </div>

      <header class="run-heading">
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

      ${run.decision ? `
        <section class="decision-band">
          <strong>${escapeHtml(run.decision.label)}</strong>
          <p>${escapeHtml(run.decision.summary)}</p>
        </section>` : ""}

      ${safeRangePanel(run)}

      <section class="metric-strip" aria-label="结果统计">${metricStrip(run.metrics)}</section>

      <section>
        <div class="section-heading">
          <div>
            <h2>对比总览</h2>
            <p>切换性别与视角；点击图片可进入大图检查。</p>
          </div>
        </div>
        <div class="segmented segmented--groups" id="groupTabs" aria-label="结果分组"></div>
        <div class="viewer">
          <div class="viewer__toolbar">
            <p id="sheetCaption"></p>
            <div class="viewer__tools">
              <button class="icon-button" id="zoomOut" type="button" aria-label="缩小" title="缩小">−</button>
              <button class="icon-button" id="zoomIn" type="button" aria-label="放大" title="放大">+</button>
              <button class="icon-button icon-button--fit" id="zoomFit" type="button" aria-label="适合窗口" title="适合窗口">适合</button>
              <button class="icon-button" id="openSheet" type="button" aria-label="打开大图" title="打开大图">↗</button>
            </div>
          </div>
          <div class="viewer__canvas"><img id="sheetImage" src="" alt=""></div>
        </div>
        <div class="segmented" id="sheetTabs" aria-label="总览视角"></div>
      </section>

      <section>
        <div class="section-heading">
          <div>
            <h2>A/B 细节对比</h2>
            <p>任意选择两个方案，在同一视角下并排检查。</p>
          </div>
        </div>
        <div class="compare-controls">
          <div class="field"><label for="compareA">方案 A</label><select class="compare-select" id="compareA"></select></div>
          <div class="field"><label for="compareB">方案 B</label><select class="compare-select" id="compareB"></select></div>
          <div class="field">
            <label for="compareView">视角</label>
            <select class="compare-select" id="compareView"></select>
          </div>
        </div>
        <div class="compare-grid">
          <article class="compare-pane">
            <div class="compare-pane__label"><strong id="compareLabelA"></strong><span>方案 A</span></div>
            <button type="button" data-compare-pane="a" aria-label="打开方案 A 大图"><img id="compareImageA" src="" alt=""></button>
          </article>
          <article class="compare-pane">
            <div class="compare-pane__label"><strong id="compareLabelB"></strong><span>方案 B</span></div>
            <button type="button" data-compare-pane="b" aria-label="打开方案 B 大图"><img id="compareImageB" src="" alt=""></button>
          </article>
        </div>
      </section>

      <section>
        <div class="section-heading">
          <div>
            <h2>参数矩阵</h2>
            <p>当前分组中每个可视化方案的受控 Morph 值。</p>
          </div>
        </div>
        <div id="profileTableTarget"></div>
      </section>

      <section>
        <div class="section-heading">
          <div>
            <h2>原始产物</h2>
            <p>运行清单、验证结果和人工审查说明。</p>
          </div>
        </div>
        <div class="artifact-list">${artifactList(run.artifacts)}</div>
      </section>
    </article>`;

  attachRunInteractions(run, initialGroup);
  app.focus({ preventScroll: true });
}

async function route() {
  const match = location.hash.match(/^#\/runs\/([^/]+)$/);
  if (!match) {
    renderHome();
    return;
  }

  const id = decodeURIComponent(match[1]);
  const entry = registry?.runs.find((run) => run.id === id);
  if (!entry) {
    showError("找不到结果分支", `没有登记 ID 为 ${id} 的结果。`);
    return;
  }

  try {
    showLoading(`正在加载 ${entry.title}...`);
    renderRun(await loadRun(entry));
  } catch (error) {
    showError("结果加载失败", error.message);
  }
}

async function bootstrap() {
  try {
    const response = await fetch("./data/registry.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    registry = await response.json();
    registryStatus.textContent = `${registry.runs.length} 个结果分支已登记`;
    await route();
  } catch (error) {
    registryStatus.textContent = "记录读取失败";
    showError("无法读取结果索引", `${error.message}。请通过本地服务打开该页面。`);
  }
}

homeButton.addEventListener("click", navigateHome);
window.addEventListener("hashchange", route);
dialogClose.addEventListener("click", () => imageDialog.close());
dialogZoomIn.addEventListener("click", () => setDialogZoom(dialogZoom * 1.2));
dialogZoomOut.addEventListener("click", () => setDialogZoom(dialogZoom / 1.2));
dialogZoomFit.addEventListener("click", () => setDialogZoom(1));
dialogImage.addEventListener("load", () => requestAnimationFrame(() => setDialogZoom(dialogZoom)));
dialogImage.addEventListener("dblclick", (event) => {
  event.preventDefault();
  const rect = dialogCanvas.getBoundingClientRect();
  setDialogZoom(dialogZoom > 1 ? 1 : 2, {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  });
});
dialogCanvas.addEventListener("wheel", (event) => {
  if (!imageDialog.open) return;
  event.preventDefault();
  const rect = dialogCanvas.getBoundingClientRect();
  const factor = event.deltaY < 0 ? 1.16 : 1 / 1.16;
  setDialogZoom(dialogZoom * factor, {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  });
}, { passive: false });
dialogCanvas.addEventListener("pointerdown", (event) => {
  if (dialogZoom <= 1 || event.button !== 0) return;
  dialogDrag = {
    pointerId: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    scrollLeft: dialogCanvas.scrollLeft,
    scrollTop: dialogCanvas.scrollTop,
  };
  dialogCanvas.setPointerCapture(event.pointerId);
  dialogCanvas.classList.add("image-dialog__canvas--dragging");
});
dialogCanvas.addEventListener("pointermove", (event) => {
  if (!dialogDrag || dialogDrag.pointerId !== event.pointerId) return;
  dialogCanvas.scrollLeft = dialogDrag.scrollLeft - (event.clientX - dialogDrag.x);
  dialogCanvas.scrollTop = dialogDrag.scrollTop - (event.clientY - dialogDrag.y);
});
function stopDialogDrag(event) {
  if (!dialogDrag || (event && dialogDrag.pointerId !== event.pointerId)) return;
  if (event && dialogCanvas.hasPointerCapture(event.pointerId)) {
    dialogCanvas.releasePointerCapture(event.pointerId);
  }
  dialogDrag = null;
  dialogCanvas.classList.remove("image-dialog__canvas--dragging");
}
dialogCanvas.addEventListener("pointerup", stopDialogDrag);
dialogCanvas.addEventListener("pointercancel", stopDialogDrag);
imageDialog.addEventListener("keydown", (event) => {
  if (event.key === "+" || event.key === "=") setDialogZoom(dialogZoom * 1.2);
  if (event.key === "-") setDialogZoom(dialogZoom / 1.2);
  if (event.key === "0") setDialogZoom(1);
});
imageDialog.addEventListener("click", (event) => {
  if (event.target === imageDialog) imageDialog.close();
});
imageDialog.addEventListener("close", () => {
  dialogDrag = null;
  dialogCanvas.classList.remove("image-dialog__canvas--dragging", "image-dialog__canvas--zoomed");
  dialogStage.removeAttribute("style");
  dialogImage.removeAttribute("style");
  dialogCanvas.scrollTo(0, 0);
});
window.addEventListener("resize", () => {
  if (imageDialog.open) setDialogZoom(dialogZoom);
});

bootstrap();

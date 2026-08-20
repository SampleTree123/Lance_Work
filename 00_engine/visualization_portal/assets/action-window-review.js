const params = new URLSearchParams(window.location.search);
const manifestUrl = params.get("manifest");
const seedSelectionUrl = params.get("selection");
if (!manifestUrl) throw new Error("Missing manifest query parameter");

const manifest = await fetch(manifestUrl).then((response) => {
  if (!response.ok) throw new Error(`Unable to load manifest: ${response.status}`);
  return response.json();
});

const cases = Array.isArray(manifest.cases) ? manifest.cases : [];
if (!cases.length) throw new Error("Manifest contains no action cases");

const duration = Number(manifest.window_duration_seconds || 5);
const storageKey = `lance-action-window:${manifest.review_id}`;
const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
const seedSelection = seedSelectionUrl
  ? await fetch(seedSelectionUrl).then((response) => {
      if (!response.ok) {
        throw new Error(`Unable to load selection seed: ${response.status}`);
      }
      return response.json();
    })
  : null;
let activeIndex = 0;
let filter = "all";
let stopAt = null;

const elements = Object.fromEntries([
  "caseList", "caseMeta", "caseTitle", "previewVideo", "currentTime",
  "windowStart", "windowStartNumber", "windowRange", "paddingNotice",
  "setFromCurrent", "resetRecommended", "previewWindow", "confirmWindow",
  "confirmAndNext", "previousCase", "nextCase", "saveState", "exportJson",
  "progressText", "progressBar",
].map((id) => [id, document.getElementById(id)]));

function formatTime(value) {
  const total = Math.max(0, Number(value) || 0);
  const minutes = Math.floor(total / 60);
  const seconds = total - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${seconds.toFixed(2).padStart(5, "0")}`;
}

function formatSex(value) {
  return value === "female" ? "女性" : value === "male" ? "男性" : value;
}

function videoUrl(item) {
  const absolute = item.video.path.replaceAll("\\", "/");
  const marker = "/Lance_Work/";
  const index = absolute.toLowerCase().indexOf(marker.toLowerCase());
  if (index < 0) throw new Error(`Video is outside Lance_Work: ${absolute}`);
  return `/${absolute.slice(index + marker.length)}`;
}

function sourceWindowDuration(item) {
  return Math.min(
    duration,
    Number(item.source_window_duration_seconds || item.video.duration_seconds),
  );
}

function maxStart(item) {
  return Math.max(0, Number(item.video.duration_seconds) - sourceWindowDuration(item));
}

function clampStart(item, value) {
  const rounded = Math.round((Number(value) || 0) * 10) / 10;
  return Math.min(maxStart(item), Math.max(0, rounded));
}

function applySeedSelection() {
  if (!seedSelection) return 0;
  const byAction = new Map(cases.map((item) => [item.action_id, item]));
  let imported = 0;
  (seedSelection.selections || []).forEach((decision) => {
    if (!decision.confirmed) return;
    const item = byAction.get(decision.action_id);
    if (!item) return;
    if (decision.case_id !== item.case_id) return;
    if (decision.source_filename !== item.source_filename) return;
    if (decision.source_video_sha256 !== item.video.sha256) return;
    if (
      Math.abs(Number(decision.production_duration_seconds) - duration) > 0.001
    ) return;
    saved[item.case_id] = {
      start_seconds: clampStart(item, decision.window_start_seconds),
      confirmed: true,
      inherited: true,
      locked: true,
    };
    imported += 1;
  });
  localStorage.setItem(storageKey, JSON.stringify(saved));
  return imported;
}

const seededConfirmedCount = applySeedSelection();

function stateFor(item) {
  return saved[item.case_id] || {
    start_seconds: clampStart(item, item.recommended_start_seconds || 0),
    confirmed: false,
  };
}

function visibleIndices() {
  return cases
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => filter === "all" || item.sex === filter)
    .map(({ index }) => index);
}

function persist() {
  localStorage.setItem(storageKey, JSON.stringify(saved));
  renderProgress();
  renderList();
}

function renderProgress() {
  const complete = cases.filter((item) => stateFor(item).confirmed).length;
  elements.progressText.textContent = `${complete} / ${cases.length}`;
  elements.progressBar.style.width = `${cases.length ? complete / cases.length * 100 : 0}%`;
}

function renderList() {
  elements.caseList.replaceChildren();
  visibleIndices().forEach((index) => {
    const item = cases[index];
    const state = stateFor(item);
    const button = document.createElement("button");
    const title = document.createElement("strong");
    const meta = document.createElement("span");
    const status = document.createElement("b");

    button.type = "button";
    button.className = "case-item";
    button.dataset.active = String(index === activeIndex);
    button.dataset.confirmed = String(Boolean(state.confirmed));
    title.textContent = item.label;
    meta.textContent = `${formatSex(item.sex)} · ${Number(item.video.duration_seconds).toFixed(2)}s`;
    status.textContent = state.confirmed ? "已确认" : "待选择";
    if (state.locked) status.textContent = "\u5df2\u786e\u8ba4\uff08\u7ee7\u627f\uff09";
    button.append(title, meta, status);
    button.addEventListener("click", () => selectCase(index));
    elements.caseList.append(button);
  });
}

function updateWindowReadout() {
  const item = cases[activeIndex];
  const start = clampStart(item, elements.windowStart.value);
  const sourceDuration = sourceWindowDuration(item);
  const sourceEnd = Math.min(Number(item.video.duration_seconds), start + sourceDuration);
  const padding = Math.max(0, duration - sourceDuration);

  elements.windowRange.textContent = `${formatTime(start)} - ${formatTime(sourceEnd)}`;
  elements.windowStart.value = start.toFixed(2);
  elements.windowStartNumber.value = start.toFixed(2);

  if (padding > 0) {
    elements.paddingNotice.hidden = false;
    elements.paddingNotice.textContent = `源动作只有 ${sourceDuration.toFixed(2)} 秒；生产时将在两端平滑补入 ${padding.toFixed(2)} 秒 subtle idle，总时长仍为 ${duration.toFixed(1)} 秒。`;
  } else {
    elements.paddingNotice.hidden = true;
    elements.paddingNotice.textContent = "";
  }
}

function updateNavigation() {
  const indices = visibleIndices();
  const position = indices.indexOf(activeIndex);
  elements.previousCase.disabled = position <= 0;
  elements.nextCase.disabled = position < 0 || position >= indices.length - 1;
  const locked = Boolean(stateFor(cases[activeIndex]).locked);
  elements.confirmWindow.disabled = locked;
  elements.confirmAndNext.disabled = elements.nextCase.disabled || locked;
}

function selectCase(index) {
  stopAt = null;
  elements.previewVideo.pause();
  activeIndex = Math.max(0, Math.min(cases.length - 1, index));
  const item = cases[activeIndex];
  const state = stateFor(item);
  const sourceDuration = sourceWindowDuration(item);
  const startLimit = maxStart(item);
  const locked = Boolean(state.locked);

  elements.caseMeta.textContent = `${formatSex(item.sex)} · ${item.review_family} · 源动作 ${Number(item.video.duration_seconds).toFixed(2)} 秒`;
  elements.caseTitle.textContent = item.label;
  elements.previewVideo.src = videoUrl(item);
  elements.windowStart.max = startLimit.toFixed(2);
  elements.windowStartNumber.max = startLimit.toFixed(2);
  elements.windowStart.disabled = sourceDuration < duration || locked;
  elements.windowStartNumber.disabled = sourceDuration < duration || locked;
  elements.setFromCurrent.disabled = sourceDuration < duration || locked;
  elements.resetRecommended.disabled = sourceDuration < duration || locked;
  elements.windowStart.value = clampStart(item, state.start_seconds).toFixed(2);
  elements.windowStartNumber.value = elements.windowStart.value;
  elements.saveState.textContent = state.confirmed ? "已确认" : "尚未确认";
  if (locked) {
    elements.saveState.textContent = "\u5df2\u4ece\u4e0a\u4e00\u7248\u9501\u5b9a";
  }
  updateWindowReadout();
  updateNavigation();
  renderList();
}

function setStart(value, confirm = false) {
  const item = cases[activeIndex];
  if (stateFor(item).locked) return;
  const start = clampStart(item, value);
  elements.windowStart.value = start.toFixed(2);
  elements.windowStartNumber.value = start.toFixed(2);
  saved[item.case_id] = { start_seconds: start, confirmed: Boolean(confirm) };
  elements.saveState.textContent = confirm ? "已确认" : "已修改，尚未确认";
  updateWindowReadout();
  persist();
}

function moveCase(offset) {
  const indices = visibleIndices();
  const position = indices.indexOf(activeIndex);
  const nextPosition = Math.max(0, Math.min(indices.length - 1, position + offset));
  if (indices[nextPosition] !== undefined && indices[nextPosition] !== activeIndex) {
    selectCase(indices[nextPosition]);
  }
}

async function previewSelection() {
  const item = cases[activeIndex];
  const start = clampStart(item, elements.windowStart.value);
  elements.previewVideo.pause();
  stopAt = null;
  await seekTo(start);
  stopAt = Math.min(Number(item.video.duration_seconds), start + sourceWindowDuration(item));
  await elements.previewVideo.play();
}

function waitForVideoEvent(eventName, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error(`Timed out waiting for video ${eventName}`));
    }, timeoutMs);
    const onEvent = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(elements.previewVideo.error || new Error("Video playback failed"));
    };
    const cleanup = () => {
      window.clearTimeout(timeout);
      elements.previewVideo.removeEventListener(eventName, onEvent);
      elements.previewVideo.removeEventListener("error", onError);
    };
    elements.previewVideo.addEventListener(eventName, onEvent, { once: true });
    elements.previewVideo.addEventListener("error", onError, { once: true });
  });
}

async function seekTo(targetSeconds) {
  if (elements.previewVideo.readyState < HTMLMediaElement.HAVE_METADATA) {
    await waitForVideoEvent("loadedmetadata");
  }
  const target = Math.min(
    Math.max(0, Number(targetSeconds) || 0),
    Number.isFinite(elements.previewVideo.duration)
      ? elements.previewVideo.duration
      : Number(targetSeconds) || 0,
  );
  if (Math.abs(elements.previewVideo.currentTime - target) <= 0.03) return;
  const seeked = waitForVideoEvent("seeked");
  elements.previewVideo.currentTime = target;
  await seeked;
}

elements.previewVideo.addEventListener("timeupdate", () => {
  elements.currentTime.textContent = formatTime(elements.previewVideo.currentTime);
  if (stopAt !== null && elements.previewVideo.currentTime >= stopAt) {
    elements.previewVideo.pause();
    stopAt = null;
  }
});
elements.previewVideo.addEventListener("loadedmetadata", () => {
  elements.previewVideo.currentTime = clampStart(cases[activeIndex], elements.windowStart.value);
});
elements.windowStart.addEventListener("input", () => setStart(elements.windowStart.value));
elements.windowStartNumber.addEventListener("change", () => setStart(elements.windowStartNumber.value));
elements.setFromCurrent.addEventListener("click", () => setStart(elements.previewVideo.currentTime));
elements.resetRecommended.addEventListener("click", () => {
  setStart(cases[activeIndex].recommended_start_seconds || 0);
});
elements.previewWindow.addEventListener("click", previewSelection);
elements.confirmWindow.addEventListener("click", () => setStart(elements.windowStart.value, true));
elements.confirmAndNext.addEventListener("click", () => {
  setStart(elements.windowStart.value, true);
  moveCase(1);
});
elements.previousCase.addEventListener("click", () => moveCase(-1));
elements.nextCase.addEventListener("click", () => moveCase(1));

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    const indices = visibleIndices();
    if (!indices.includes(activeIndex)) activeIndex = indices[0];
    selectCase(activeIndex);
  });
});

elements.exportJson.addEventListener("click", () => {
  const selections = cases.map((item) => {
    const state = stateFor(item);
    const sourceDuration = sourceWindowDuration(item);
    const sourceEnd = Math.min(
      Number(item.video.duration_seconds),
      Number(state.start_seconds || 0) + sourceDuration,
    );
    return {
      action_id: item.action_id,
      case_id: item.case_id,
      sex: item.sex,
      source_filename: item.source_filename,
      source_video_sha256: item.video.sha256,
      source_duration_seconds: Number(Number(item.video.duration_seconds).toFixed(6)),
      window_start_seconds: Number(Number(state.start_seconds || 0).toFixed(2)),
      window_end_seconds: Number(sourceEnd.toFixed(6)),
      source_window_duration_seconds: Number(sourceDuration.toFixed(6)),
      production_duration_seconds: duration,
      padding_required_seconds: Number(Math.max(0, duration - sourceDuration).toFixed(6)),
      padding_policy: item.padding_policy || "none",
      confirmed: Boolean(state.confirmed),
      inherited_from_seed: Boolean(state.inherited),
    };
  });
  const payload = {
    schema_version: 2,
    review_id: manifest.review_id,
    source_manifest_url: manifestUrl,
    exported_at: new Date().toISOString(),
    production_window_duration_seconds: duration,
    complete: selections.every((item) => item.confirmed),
    confirmed_count: selections.filter((item) => item.confirmed).length,
    seed_selection_url: seedSelectionUrl,
    seeded_confirmed_count: seededConfirmedCount,
    selections,
  };
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${manifest.review_id}_selection.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 0);
});

document.title = `${cases.length} 个动作 · ${duration.toFixed(0)} 秒窗口选择`;
elements.previewWindow.textContent = `预览这 ${duration.toFixed(0)} 秒`;
renderProgress();
const firstPendingIndex = cases.findIndex((item) => !stateFor(item).confirmed);
selectCase(firstPendingIndex >= 0 ? firstPendingIndex : 0);

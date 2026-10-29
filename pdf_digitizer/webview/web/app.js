(() => {
  "use strict";

  const AXIS_KEYS = ["X1", "X2", "Y1", "Y2"];
  const DEFAULT_VALUES = [0, 100, 0, 100];
  const MAG_SIZE = 150;
  const MAG_SRC = 60;
  const MIN_SCALE = 0.05;
  const MAX_SCALE = 8;
  const ZOOM_FACTOR = 1.12;
  const PREVIEW_LIMIT = 2000;
  const MAG_MOVE_THRESHOLD = 2;

  const el = (id) => document.getElementById(id);

  const dom = {
    canvas: el("canvas"),
    stage: el("stage"),
    status: el("status"),
    calibrate: el("btn-calibrate"),
    reset: el("btn-reset"),
    pick: el("btn-pick"),
    logx: el("logx"),
    logy: el("logy"),
    calibEntry: el("calib-entry"),
    calibLabel: el("calib-label"),
    calibInput: el("calib-input"),
    calibOk: el("calib-ok"),
    modal: el("data-modal"),
    modalClose: el("modal-close"),
    fXmin: el("f-xmin"),
    fXmax: el("f-xmax"),
    fYmin: el("f-ymin"),
    fYmax: el("f-ymax"),
    refresh: el("btn-refresh"),
    stride: el("stride"),
    separator: el("separator"),
    copy: el("btn-copy"),
    save: el("btn-save"),
    count: el("count"),
    tbody: el("table-body"),
    thX: el("th-x"),
    thY: el("th-y"),
    toast: el("toast"),
  };

  const state = {
    image: null,
    iw: 0,
    ih: 0,
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    autoFit: true,
    mode: "VIEW",
    step: 0,
    markers: [],
    highlight: [],
    pending: null,
    mouse: { x: 0, y: 0, inside: false },
    lang: "CN",
    strings: {},
    sortCol: null,
    sortDesc: false,
    cssW: 1,
    cssH: 1,
    ready: false,
  };

  let ctx = null;
  let dpr = window.devicePixelRatio || 1;
  let pan = null;
  let suppressClick = false;
  let toastTimer = null;
  let renderQueued = false;
  let lastRenderMouse = null;

  const api = () => window.pywebview.api;

  // --- 基础工具 ---

  const clamp = (value, low, high) => Math.max(low, Math.min(value, high));

  function formatNumber(value, digits = 6) {
    if (!Number.isFinite(value)) return String(value);
    if (value === 0) return "0";
    return String(Number(value.toPrecision(digits)));
  }

  function parseOptional(text) {
    const trimmed = String(text || "").trim();
    if (!trimmed) return null;
    const value = Number.parseFloat(trimmed);
    return Number.isFinite(value) ? value : null;
  }

  function setStatus(text) {
    dom.status.textContent = text;
  }

  function toast(message, isError = false) {
    dom.toast.textContent = message;
    dom.toast.classList.toggle("error", Boolean(isError));
    dom.toast.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => dom.toast.classList.add("hidden"), 2200);
  }

  // --- 画布 ---

  function resizeCanvas() {
    if (!ctx) return;
    const rect = dom.stage.getBoundingClientRect();
    state.cssW = Math.max(1, Math.floor(rect.width));
    state.cssH = Math.max(1, Math.floor(rect.height));
    dpr = window.devicePixelRatio || 1;
    dom.canvas.width = Math.floor(state.cssW * dpr);
    dom.canvas.height = Math.floor(state.cssH * dpr);
    if (state.image && state.autoFit) {
      fit(false);
    }
    render();
  }

  function fit(shouldRender = true) {
    if (!state.image) {
      if (shouldRender) render();
      return;
    }
    const scaleX = state.cssW / state.iw;
    const scaleY = state.cssH / state.ih;
    state.scale = Math.min(scaleX, scaleY);
    state.offsetX = (state.cssW - state.iw * state.scale) / 2;
    state.offsetY = (state.cssH - state.ih * state.scale) / 2;
    state.autoFit = true;
    if (shouldRender) render();
  }

  function zoomAt(canvasX, canvasY, factor) {
    if (!state.image) return;
    const previous = state.scale;
    const next = clamp(previous * factor, MIN_SCALE, MAX_SCALE);
    if (Math.abs(next - previous) < 1e-9) return;
    const imageX = (canvasX - state.offsetX) / previous;
    const imageY = (canvasY - state.offsetY) / previous;
    state.scale = next;
    state.offsetX = canvasX - imageX * next;
    state.offsetY = canvasY - imageY * next;
    state.autoFit = false;
    render();
  }

  function zoomCenter(factor) {
    zoomAt(state.cssW / 2, state.cssH / 2, factor);
  }

  function requestRender() {
    if (renderQueued) return;
    renderQueued = true;
    window.requestAnimationFrame(() => {
      renderQueued = false;
      render();
    });
  }

  function render() {
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, state.cssW, state.cssH);
    ctx.fillStyle = "#50565d";
    ctx.fillRect(0, 0, state.cssW, state.cssH);

    if (!state.image) return;

    ctx.imageSmoothingEnabled = state.scale < 1;
    ctx.drawImage(
      state.image,
      state.offsetX,
      state.offsetY,
      state.iw * state.scale,
      state.ih * state.scale
    );

    drawHighlight();
    drawMarkers();
    drawMagnifier();
  }

  function drawHighlight() {
    if (state.highlight.length < 2) return;
    ctx.save();
    ctx.strokeStyle = "#00e5ff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    state.highlight.forEach(([relX, relY], index) => {
      const x = state.offsetX + relX * state.iw * state.scale;
      const y = state.offsetY + relY * state.ih * state.scale;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  }

  function drawMarkers() {
    if (!state.markers.length) return;
    ctx.save();
    ctx.font = "700 13px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    for (const marker of state.markers) {
      const x = state.offsetX + marker.rx * state.iw * state.scale;
      const y = state.offsetY + marker.ry * state.ih * state.scale;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#00ff66";
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = "#0b2a12";
      ctx.stroke();

      const label = `${marker.key}=${formatNumber(marker.value)}`;
      ctx.lineWidth = 3;
      ctx.strokeStyle = "rgba(0, 0, 0, 0.55)";
      ctx.strokeText(label, x + 7, y - 7);
      ctx.fillStyle = "#00ff66";
      ctx.fillText(label, x + 7, y - 7);
    }
    ctx.restore();
  }

  function drawMagnifier() {
    if (
      state.mode !== "SET_AXIS" ||
      !state.mouse.inside ||
      state.pending ||
      !state.image
    ) {
      return;
    }
    const imageX = (state.mouse.x - state.offsetX) / state.scale;
    const imageY = (state.mouse.y - state.offsetY) / state.scale;
    if (imageX < 0 || imageY < 0 || imageX > state.iw || imageY > state.ih) return;

    const sourceX = clamp(imageX - MAG_SRC / 2, 0, Math.max(0, state.iw - MAG_SRC));
    const sourceY = clamp(imageY - MAG_SRC / 2, 0, Math.max(0, state.ih - MAG_SRC));

    let destX = state.mouse.x + 24;
    let destY = state.mouse.y - MAG_SIZE - 24;
    if (destY < 0) destY = state.mouse.y + 24;
    destX = clamp(destX, 0, Math.max(0, state.cssW - MAG_SIZE));
    destY = clamp(destY, 0, Math.max(0, state.cssH - MAG_SIZE));

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(
      state.image,
      sourceX,
      sourceY,
      MAG_SRC,
      MAG_SRC,
      destX,
      destY,
      MAG_SIZE,
      MAG_SIZE
    );
    ctx.strokeStyle = "#0078d7";
    ctx.lineWidth = 2;
    ctx.strokeRect(destX + 1, destY + 1, MAG_SIZE - 2, MAG_SIZE - 2);

    const centreX = destX + MAG_SIZE / 2;
    const centreY = destY + MAG_SIZE / 2;
    ctx.strokeStyle = "#ff3b30";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(centreX, destY);
    ctx.lineTo(centreX, destY + MAG_SIZE);
    ctx.moveTo(destX, centreY);
    ctx.lineTo(destX + MAG_SIZE, centreY);
    ctx.stroke();

    const ratio = MAG_SIZE / MAG_SRC;
    ctx.font = "700 11px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.fillStyle = "#00ff66";
    for (const marker of state.markers) {
      const markerX = marker.rx * state.iw;
      const markerY = marker.ry * state.ih;
      if (
        markerX < sourceX ||
        markerX > sourceX + MAG_SRC ||
        markerY < sourceY ||
        markerY > sourceY + MAG_SRC
      ) {
        continue;
      }
      const localX = destX + (markerX - sourceX) * ratio;
      const localY = destY + (markerY - sourceY) * ratio;
      ctx.beginPath();
      ctx.arc(localX, localY, 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#00ff66";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillText(marker.key, localX + 6, localY - 5);
    }
    ctx.restore();
  }

  // --- 鼠标 ---

  function pointerPos(event) {
    const rect = dom.canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  function updateCursor() {
    if (pan) {
      dom.canvas.style.cursor = "grabbing";
      return;
    }
    if (state.mode === "SET_AXIS") dom.canvas.style.cursor = "crosshair";
    else if (state.mode === "SELECT_CURVE") dom.canvas.style.cursor = "pointer";
    else dom.canvas.style.cursor = "default";
  }

  function imageCoords(canvasX, canvasY) {
    return {
      x: (canvasX - state.offsetX) / state.scale,
      y: (canvasY - state.offsetY) / state.scale,
    };
  }

  function bindCanvasEvents() {
    dom.canvas.addEventListener("mousemove", (event) => {
      if (!state.image) return;
      const position = pointerPos(event);
      state.mouse.x = position.x;
      state.mouse.y = position.y;
      state.mouse.inside = true;

      if (pan) {
        const dx = event.clientX - pan.startX;
        const dy = event.clientY - pan.startY;
        if (Math.hypot(dx, dy) > 3) pan.moved = true;
        state.offsetX = pan.offsetX + dx;
        state.offsetY = pan.offsetY + dy;
        state.autoFit = false;
        requestRender();
        return;
      }

      if (state.mode !== "SET_AXIS" || state.pending) return;
      if (
        lastRenderMouse &&
        Math.abs(position.x - lastRenderMouse.x) < MAG_MOVE_THRESHOLD &&
        Math.abs(position.y - lastRenderMouse.y) < MAG_MOVE_THRESHOLD
      ) {
        return;
      }
      lastRenderMouse = position;
      requestRender();
    });

    dom.canvas.addEventListener("mouseleave", () => {
      state.mouse.inside = false;
      requestRender();
    });

    dom.canvas.addEventListener("click", (event) => {
      if (!state.image || event.button !== 0) return;
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      const position = pointerPos(event);
      const image = imageCoords(position.x, position.y);
      if (
        image.x < 0 ||
        image.y < 0 ||
        image.x > state.iw ||
        image.y > state.ih
      ) {
        return;
      }
      handleCanvasClick(position, image);
    });

    dom.canvas.addEventListener(
      "wheel",
      (event) => {
        if (!state.image) return;
        event.preventDefault();
        const position = pointerPos(event);
        zoomAt(
          position.x,
          position.y,
          event.deltaY < 0 ? ZOOM_FACTOR : 1 / ZOOM_FACTOR
        );
      },
      { passive: false }
    );

    dom.canvas.addEventListener("mousedown", (event) => {
      if (!state.image) return;
      const middle = event.button === 1;
      const leftInView = event.button === 0 && state.mode === "VIEW";
      if (!middle && !leftInView) return;
      event.preventDefault();
      suppressClick = false;
      pan = {
        startX: event.clientX,
        startY: event.clientY,
        offsetX: state.offsetX,
        offsetY: state.offsetY,
        moved: false,
      };
      updateCursor();
    });

    window.addEventListener("mouseup", () => {
      if (!pan) return;
      suppressClick = Boolean(pan.moved);
      pan = null;
      updateCursor();
    });

    dom.canvas.addEventListener("dblclick", () => {
      if (state.image) fit();
    });
  }

  async function handleCanvasClick(position, image) {
    if (state.mode === "SET_AXIS") {
      state.pending = {
        index: state.step,
        rx: image.x / state.iw,
        ry: image.y / state.ih,
      };
      showCalibInput(position.x, position.y);
      render();
      return;
    }
    if (state.mode === "SELECT_CURVE") {
      await pickAt(image.x / state.iw, image.y / state.ih);
      return;
    }
    setStatus(state.strings.msg_need_axis || "");
  }

  // --- 定标输入条 ---

  function showCalibInput(canvasX, canvasY) {
    const key = AXIS_KEYS[state.pending.index];
    dom.calibLabel.textContent = `${key} =`;
    dom.calibInput.value = String(DEFAULT_VALUES[state.pending.index]);
    dom.calibInput.classList.remove("invalid");
    dom.calibEntry.classList.remove("hidden");

    const rect = dom.calibEntry.getBoundingClientRect();
    let left = canvasX + 18;
    let top = canvasY - rect.height - 10;
    if (left + rect.width > state.cssW) left = canvasX - rect.width - 18;
    left = clamp(left, 0, Math.max(0, state.cssW - rect.width));
    top = clamp(top, 0, Math.max(0, state.cssH - rect.height));
    dom.calibEntry.style.left = `${left}px`;
    dom.calibEntry.style.top = `${top}px`;

    dom.calibInput.focus();
    dom.calibInput.select();
  }

  function hideCalibInput() {
    dom.calibEntry.classList.add("hidden");
  }

  async function confirmCalib() {
    if (!state.pending) return;
    const value = Number.parseFloat(dom.calibInput.value);
    if (!Number.isFinite(value)) {
      dom.calibInput.classList.add("invalid");
      return;
    }
    const pending = state.pending;
    let result;
    try {
      result = await api().record_calibration(
        pending.index,
        pending.rx,
        pending.ry,
        value
      );
    } catch (error) {
      toast(String(error), true);
      return;
    }
    if (!result.ok) {
      dom.calibInput.classList.add("invalid");
      setStatus(result.error || "Invalid value");
      return;
    }

    state.markers.push({
      rx: pending.rx,
      ry: pending.ry,
      value,
      key: AXIS_KEYS[pending.index],
    });
    state.pending = null;
    hideCalibInput();
    state.step = pending.index + 1;

    if (result.complete) {
      state.mode = "VIEW";
      dom.calibrate.disabled = true;
      dom.pick.disabled = false;
      setStatus(doneText());
    } else {
      setStatus(
        (state.strings.status_axis || "") + (AXIS_KEYS[state.step] || "")
      );
    }
    updateCursor();
    render();
  }

  function cancelCalib() {
    state.pending = null;
    hideCalibInput();
    updateStatusFromState();
    render();
  }

  function doneText() {
    const modeX = dom.logx.checked ? "Log" : "Lin";
    const modeY = dom.logy.checked ? "Log" : "Lin";
    return `${state.strings.status_done || ""} | X:${modeX} Y:${modeY}`;
  }

  function updateStatusFromState() {
    const strings = state.strings;
    if (state.mode === "SET_AXIS") {
      setStatus(
        (strings.status_axis || "") + (AXIS_KEYS[state.step] || "")
      );
    } else if (state.mode === "SELECT_CURVE") {
      setStatus(strings.status_pick || "");
    } else if (state.markers.length >= AXIS_KEYS.length) {
      setStatus(doneText());
    } else {
      setStatus(strings.status_ready || "");
    }
  }

  // --- 文档与提取 ---

  async function openPdf() {
    let result;
    try {
      result = await api().open_pdf();
    } catch (error) {
      toast(String(error), true);
      return;
    }
    if (!result.ok) {
      if (result.error) toast(result.error, true);
      return;
    }

    const image = new Image();
    image.onload = () => {
      state.image = image;
      state.iw = result.width;
      state.ih = result.height;
      state.markers = [];
      state.highlight = [];
      state.mode = "VIEW";
      state.step = 0;
      state.pending = null;
      lastRenderMouse = null;
      hideCalibInput();
      dom.calibrate.disabled = false;
      dom.reset.disabled = false;
      dom.pick.disabled = true;
      updateCursor();
      fit();
      setStatus(state.strings.status_ready || "");
    };
    image.onerror = () => toast("无法加载页面图像", true);
    image.src = result.image;
  }

  async function startCalibration() {
    if (!state.image) return;
    try {
      await api().reset_calibration();
    } catch (error) {
      toast(String(error), true);
      return;
    }
    state.mode = "SET_AXIS";
    state.step = 0;
    state.pending = null;
    state.markers = [];
    lastRenderMouse = null;
    hideCalibInput();
    dom.calibrate.disabled = true;
    dom.pick.disabled = true;
    updateCursor();
    updateStatusFromState();
    render();
  }

  async function resetCalibration() {
    try {
      await api().reset_calibration();
    } catch (error) {
      toast(String(error), true);
      return;
    }
    state.mode = "VIEW";
    state.step = 0;
    state.pending = null;
    state.markers = [];
    state.highlight = [];
    hideCalibInput();
    dom.calibrate.disabled = !state.image;
    dom.pick.disabled = true;
    updateCursor();
    updateStatusFromState();
    render();
  }

  function startPick() {
    if (!state.image) return;
    state.mode = "SELECT_CURVE";
    state.pending = null;
    hideCalibInput();
    updateCursor();
    updateStatusFromState();
    render();
  }

  async function pickAt(relX, relY) {
    let result;
    try {
      result = await api().pick_curve(
        relX,
        relY,
        dom.logx.checked,
        dom.logy.checked
      );
    } catch (error) {
      toast(String(error), true);
      return;
    }
    if (!result.ok) {
      if (result.error === "no_curve") {
        setStatus(state.strings.msg_no_curve || "No vector data");
      } else {
        setStatus(result.error || "Pick failed");
      }
      return;
    }
    state.highlight = result.highlight || [];
    render();
    openDataModal();
  }

  // --- 数据窗口 ---

  function collectFilters() {
    let step = Number.parseInt(dom.stride.value, 10);
    if (!Number.isFinite(step) || step < 1) step = 1;
    return {
      xmin: parseOptional(dom.fXmin.value),
      xmax: parseOptional(dom.fXmax.value),
      ymin: parseOptional(dom.fYmin.value),
      ymax: parseOptional(dom.fYmax.value),
      step,
      sort_col: state.sortCol,
      desc: state.sortDesc,
    };
  }

  function currentSeparator() {
    return dom.separator.value;
  }

  async function refreshData() {
    let result;
    try {
      result = await api().process_data(collectFilters());
    } catch (error) {
      toast(String(error), true);
      return;
    }
    renderTable(result.rows || []);
    const total = result.total || 0;
    let text = `Total: ${total} pts`;
    if (total > PREVIEW_LIMIT) {
      text += " | Previewing top 2000 (Export for all)";
    }
    dom.count.textContent = text;
  }

  function renderTable(rows) {
    const fragment = document.createDocumentFragment();
    rows.forEach(([x, y], index) => {
      const row = document.createElement("tr");
      const values = [String(index + 1), formatNumber(x), formatNumber(y)];
      values.forEach((text) => {
        const cell = document.createElement("td");
        cell.textContent = text;
        row.appendChild(cell);
      });
      fragment.appendChild(row);
    });
    dom.tbody.replaceChildren(fragment);
  }

  function toggleSort(column) {
    if (state.sortCol === column) state.sortDesc = !state.sortDesc;
    else {
      state.sortCol = column;
      state.sortDesc = false;
    }
    updateSortHeaders();
    refreshData();
  }

  function updateSortHeaders() {
    const arrow = state.sortDesc ? " ▼" : " ▲";
    const labelX = state.strings.col_x || "X";
    const labelY = state.strings.col_y || "Y";
    dom.thX.textContent = state.sortCol === 1 ? labelX + arrow : labelX;
    dom.thY.textContent = state.sortCol === 2 ? labelY + arrow : labelY;
  }

  function openDataModal() {
    dom.modal.classList.remove("hidden");
    refreshData();
  }

  function closeDataModal() {
    dom.modal.classList.add("hidden");
  }

  async function copyData() {
    let text;
    try {
      text = await api().copy_text(collectFilters(), currentSeparator());
    } catch (error) {
      toast(String(error), true);
      return;
    }
    try {
      await writeClipboard(text);
      toast(state.strings.msg_copy_ok || "Copied");
    } catch (error) {
      toast(String(error), true);
    }
  }

  async function writeClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }

  async function saveData() {
    let result;
    try {
      result = await api().save_export(collectFilters(), currentSeparator());
    } catch (error) {
      toast(String(error), true);
      return;
    }
    if (result.ok) {
      toast(state.strings.msg_save_ok || "Saved");
    } else if (result.error) {
      toast(result.error, true);
    }
  }

  // --- 语言 ---

  async function setLanguage(lang) {
    state.lang = lang;
    try {
      state.strings = await api().get_strings(lang);
    } catch (error) {
      toast(String(error), true);
      return;
    }
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.dataset.i18n;
      if (state.strings[key] !== undefined) {
        node.textContent = state.strings[key];
      }
    });
    updateSortHeaders();
    updateStatusFromState();
  }

  // --- 事件绑定 ---

  const actions = {
    open: openPdf,
    "zoom-in": () => zoomCenter(ZOOM_FACTOR),
    "zoom-out": () => zoomCenter(1 / ZOOM_FACTOR),
    fit: () => fit(),
    lang: () => setLanguage(state.lang === "CN" ? "EN" : "CN"),
    calibrate: startCalibration,
    reset: resetCalibration,
    pick: startPick,
    data: openDataModal,
    exit: () => api().close_window(),
  };

  function bindEvents() {
    bindCanvasEvents();

    el("toolbar").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button || button.disabled) return;
      const action = actions[button.dataset.action];
      if (action) action();
    });

    dom.calibOk.addEventListener("click", confirmCalib);
    dom.calibInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        confirmCalib();
      } else if (event.key === "Escape") {
        event.preventDefault();
        cancelCalib();
      }
    });

    dom.modalClose.addEventListener("click", closeDataModal);
    dom.modal.addEventListener("click", (event) => {
      if (event.target === dom.modal) closeDataModal();
    });

    dom.refresh.addEventListener("click", refreshData);
    [dom.fXmin, dom.fXmax, dom.fYmin, dom.fYmax].forEach((input) => {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          refreshData();
        }
      });
    });
    dom.stride.addEventListener("change", refreshData);
    dom.copy.addEventListener("click", copyData);
    dom.save.addEventListener("click", saveData);
    dom.thX.addEventListener("click", () => toggleSort(1));
    dom.thY.addEventListener("click", () => toggleSort(2));
    dom.logx.addEventListener("change", updateStatusFromState);
    dom.logy.addEventListener("change", updateStatusFromState);

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        if (!dom.modal.classList.contains("hidden")) {
          closeDataModal();
        } else if (state.pending) {
          cancelCalib();
        }
        return;
      }
      if (!(event.metaKey || event.ctrlKey)) return;
      const key = event.key.toLowerCase();
      if (key === "o") {
        event.preventDefault();
        openPdf();
      } else if (key === "=" || key === "+") {
        event.preventDefault();
        zoomCenter(ZOOM_FACTOR);
      } else if (key === "-") {
        event.preventDefault();
        zoomCenter(1 / ZOOM_FACTOR);
      } else if (key === "0") {
        event.preventDefault();
        fit();
      }
    });
  }

  function bootstrap() {
    if (state.ready) return;
    state.ready = true;
    ctx = dom.canvas.getContext("2d");
    bindEvents();
    resizeCanvas();
    new ResizeObserver(resizeCanvas).observe(dom.stage);
    setStatus("就绪 - 请打开 PDF");
    setLanguage("CN");
  }

  if (window.pywebview && window.pywebview.api) {
    bootstrap();
  } else {
    window.addEventListener("pywebviewready", bootstrap, { once: true });
  }
})();

// Datastar applies one server-rendered section per request. The originating
// element identifies that request even when a newer one uses the same URL.
import { createHorizontalTableOverflowController, createStickyTableHeaderController,
  isEligibleTableStateClick } from "./sticky-header.js";
import { changeSelection, restoreSelection } from "./selection.js";

const selector = "[data-interactive-table][data-table-query-keys]";
const instances = new WeakMap();
const requests = new WeakMap();

function initialize(root) {
  const state = {
    active: null, retry: null, timer: 0, committedURL: location.href, selected: new Set(),
    sticky: createStickyTableHeaderController(root),
    overflow: createHorizontalTableOverflowController(root),
  };
  instances.set(root, state);
  state.sticky.start();
  state.overflow.start();
  syncDisclosures(root);
  return state;
}

function stateFor(root) {
  return instances.get(root) || initialize(root);
}

function syncDisclosures(root) {
  const details = root.querySelector("[data-table-filter-disclosure]");
  if (details && !details.dataset.userToggled) {
    const count = Number(details.dataset.tableFilterCount);
    const active = Number(details.querySelector("[data-table-active-filter-count]")?.dataset.tableActiveFilterCount);
    details.open = !!active || (count <= 2 && matchMedia("(min-width: 80rem)").matches);
  }
}

function keys(root) {
  return root.dataset.tableQueryKeys.split(/\s+/).filter(Boolean);
}

function ownedState(root, url) {
  const params = new URL(url).searchParams;
  return JSON.stringify(keys(root).map(name => params.getAll(name)));
}

function copyKeys(into, from, fields) {
  for (const name of fields) {
    into.delete(name);
    for (const value of from.getAll(name)) into.append(name, value);
  }
}

function pageURL(root, target) {
  const url = new URL(location.href);
  const incoming = new URL(target, url);
  copyKeys(url.searchParams, incoming.searchParams, keys(root));
  return url;
}

function formURL(root, form) {
  const url = new URL(location.href);
  const fields = new FormData(form);
  copyKeys(url.searchParams, fields, keys(root));
  return url;
}

// A sibling may have finished since the server rendered these links. Keep
// conventional open-in-new-tab links, return URLs and GET forms shareable.
function synchronizeLinks(root, fields) {
  const page = new URL(location.href);
  for (const link of root.querySelectorAll("a[href], [data-table-row-details-url]")) {
    const isLink = link.matches("a");
    const url = new URL(isLink ? link.href : link.dataset.tableRowDetailsUrl, page);
    if (url.origin !== page.origin) continue;
    if (url.pathname === page.pathname) {
      copyKeys(url.searchParams, page.searchParams, fields);
    } else if (url.searchParams.has("next")) {
      const next = new URL(url.searchParams.get("next"), page);
      if (next.origin !== page.origin || next.pathname !== page.pathname) continue;
      copyKeys(next.searchParams, page.searchParams, fields);
      url.searchParams.set("next", next.pathname + next.search);
    } else continue;
    if (isLink) link.href = url.href;
    else link.dataset.tableRowDetailsUrl = url.pathname + url.search;
  }
  const form = root.querySelector("[data-table-filter]");
  if (!form) return;
  for (const field of form.querySelectorAll("[data-table-context-field]")) {
    if (fields.includes(field.name)) field.remove();
  }
  for (const name of fields) {
    for (const value of page.searchParams.getAll(name)) {
      const field = document.createElement("input");
      field.type = "hidden";
      field.name = name;
      field.value = value;
      field.dataset.tableContextField = "";
      form.append(field);
    }
  }
}

function cancel(state) {
  clearTimeout(state.timer);
  if (state.active) {
    state.active.controller.abort();
    state.active.trigger.remove();
    state.active = null;
  }
}

function setBusy(root, busy) {
  root.setAttribute("aria-busy", String(busy));
  const indicator = root.querySelector("[data-table-loading-status]");
  if (indicator) indicator.hidden = !busy;
}

function refresh(root, target, mode, delay = 0) {
  const state = stateFor(root);
  cancel(state);
  state.retry = { target, mode };
  setBusy(root, true);
  root.querySelector("[data-table-refresh-error]").hidden = true;
  root.querySelector("[data-table-refresh-success]").hidden = true;
  state.timer = setTimeout(() => {
    const page = pageURL(root, target);
    const endpoint = new URL(root.dataset.tableEndpoint || page.pathname, location.href);
    const fixed = new URLSearchParams(endpoint.search);
    endpoint.search = page.search;
    copyKeys(endpoint.searchParams, fixed, new Set(fixed.keys()));

    const trigger = document.createElement("span");
    trigger.hidden = true;
    const controller = new AbortController();
    const request = { root, state, trigger, controller, mode, target };
    state.active = request;
    requests.set(trigger, request);
    trigger.requestURL = endpoint.href;
    trigger.requestOptions = {
      headers: { "X-Table-Instance": root.dataset.tableInstance,
        "X-Table-Path": page.pathname + page.search },
      payload: {}, requestCancellation: controller, openWhenHidden: true,
      retry: "never", retryMaxCount: 0,
    };
    trigger.setAttribute("data-init", "@get(el.requestURL, el.requestOptions)");
    document.body.append(trigger);
  }, delay);
}

function focusBeforePatch(root) {
  const active = document.activeElement;
  if (!root.contains(active) || !(active instanceof HTMLElement)) return null;
  const search = active.matches("[data-table-search-input]");
  return { id: active.id, key: active.dataset.tableFocusKey, top: active.getBoundingClientRect().top,
    search: search || active.matches("[data-table-clear-action], [data-table-retry]"),
    range: search ? [active.selectionStart, active.selectionEnd, active.selectionDirection] : null };
}

function restoreFocus(root, focus) {
  if (!focus) return;
  const target = (focus.id && root.querySelector("#" + CSS.escape(focus.id))) ||
    (focus.key && root.querySelector('[data-table-focus-key="' + CSS.escape(focus.key) + '"]')) ||
    (focus.search && root.querySelector("[data-table-search-input]")) ||
    root.querySelector("[data-table-filter] summary, [data-table-filter] select");
  if (!target) return;
  const disclosure = target.closest("details");
  if (disclosure) disclosure.open = true;
  target.focus({preventScroll: true});
  if (focus.key) window.scrollBy({top: target.getBoundingClientRect().top - focus.top, behavior: "instant"});
  if (focus.range && target.type === "search") target.setSelectionRange(...focus.range);
}

function commit(request, focus, disclosures) {
  let { root, state } = request;
  if (state.active !== request) return;
  const replacement = document.getElementById(root.id);
  if (!replacement || !replacement.dataset.tableUrl) return;
  if (root !== replacement) {
    const selected = state.selected;
    state.sticky.dispose?.();
    state.overflow.teardown();
    root = replacement;
    state = stateFor(root);
    state.selected = selected;
  }
  root.dataset.tableEnhanced = "true";
  const url = pageURL(root, request.mode === "restore" ? request.target : root.dataset.tableUrl);
  if (ownedState(root, url) !== ownedState(root, location.href)) {
    history[request.mode === "push" ? "pushState" : "replaceState"](history.state, "", url);
  }
  for (const sibling of document.querySelectorAll(selector)) {
    if (sibling === root) continue;
    synchronizeLinks(sibling, keys(root));
    synchronizeLinks(root, keys(sibling));
  }
  state.committedURL = location.href;
  state.active = null;
  state.retry = null;
  state.overflow.rebuild();
  state.sticky.rebuild();
  syncDisclosures(root);
  for (const [selector, open] of disclosures) {
    const details = root.querySelector(selector);
    if (details) details.open = open;
  }
  restoreSelection(root, state.selected);
  setBusy(root, false);
  root.querySelector("[data-table-refresh-success]").hidden = false;
  if (request.mode === "replace") {
    const input = root.querySelector("[data-table-search-input]");
    if (input) input.value = new URL(request.target).searchParams.get(input.name) || "";
  }
  restoreFocus(root, focus);
}

// Capture precedes Datastar's document watcher. A stale response cannot reach
// its DOM patcher, including during the debounce before the next fetch starts.
document.addEventListener("datastar-fetch", event => {
  const {el, type, argsRaw} = event.detail;
  const request = requests.get(el);
  if (!request) return;
  const {root, state} = request;
  if (type === "finished") el.remove();
  if (state.active !== request || !root.isConnected) {
    event.stopImmediatePropagation();
    return;
  }
  if (type === "datastar-patch-elements") {
    const html = document.createElement("template");
    html.innerHTML = argsRaw.elements;
    const section = html.content.firstElementChild;
    if (section?.id !== root.id || !section.matches(selector)) {
      event.stopImmediatePropagation();
      return;
    }
    const focus = focusBeforePatch(root);
    const disclosures = [];
    for (const selector of ["[data-table-collapsed-search]", "[data-table-filter-disclosure]", "[data-table-mobile-sort]"]) {
      const details = root.querySelector(selector);
      if (details) disclosures.push([selector, details.open]);
    }
    state.sticky.teardown();
    request.received = true;
    queueMicrotask(() => commit(request, focus, disclosures));
  } else if (type === "error" || type === "retries-failed" || (type === "finished" && !request.received)) {
    state.active = null;
    if (request.mode === "restore") {
      history.replaceState(history.state, "", pageURL(root, state.committedURL));
      for (const sibling of document.querySelectorAll(selector)) {
        if (sibling !== root) synchronizeLinks(sibling, keys(root));
      }
    }
    setBusy(root, false);
    root.querySelector("[data-table-refresh-error]").hidden = false;
  }
}, true);

function enhanced(target) {
  return target.closest?.(selector + '[data-table-enhanced="true"]');
}

document.addEventListener("input", event => {
  const root = enhanced(event.target);
  if (root && event.target.matches("[data-table-search-input]") && !event.isComposing) {
    refresh(root, formURL(root, event.target.form), "replace", 300);
  }
});

document.addEventListener("change", event => {
  const target = event.target;
  const root = enhanced(target);
  if (!root) return;
  if (target.matches("[data-table-row-select], [data-table-select-page]")) {
    changeSelection(root, stateFor(root).selected, target);
  } else if (target.matches("[data-table-filter] select, [data-table-filter] input[type=date]")) {
    refresh(root, formURL(root, target.form), "push");
  }
});

document.addEventListener("submit", event => {
  const form = event.target;
  const root = enhanced(form);
  if (!root) return;
  if (form.matches("[data-table-filter]")) {
    event.preventDefault();
    refresh(root, formURL(root, form), "replace");
  }
});

document.addEventListener("formdata", event => {
  const form = event.target;
  if (!form.matches("[data-table-selection-action]")) return;
  const root = form.closest(selector);
  if (root) for (const key of stateFor(root).selected) event.formData.append("selected", key);
}, true);

document.addEventListener("click", event => {
  const root = enhanced(event.target);
  if (!root || !isEligibleTableStateClick(event)) return;
  const state = stateFor(root);
  const link = event.target.closest("a[data-table-state-url]");
  if (link) {
    event.preventDefault();
    refresh(root, link.href, "push");
  } else if (event.target.closest("[data-table-retry]") && state.retry) {
    refresh(root, state.retry.target, state.retry.mode);
  } else if (event.target.closest("[data-table-selection-clear]")) {
    state.selected.clear();
    restoreSelection(root, state.selected);
  } else if (event.target.closest("[data-table-filter-disclosure] summary")) {
    event.target.closest("details").dataset.userToggled = "true";
  }
});

document.addEventListener("toggle", event => {
  const details = event.target;
  if (!details.matches?.("[data-table-collapsed-search]") || !details.contains(document.activeElement)) return;
  const input = details.querySelector("[data-table-search-input]");
  if (details.open) input?.focus({preventScroll: true});
  else if (input?.value) details.open = true;
}, true);

window.addEventListener("popstate", () => {
  for (const root of document.querySelectorAll(selector + '[data-table-enhanced="true"]')) {
    const state = stateFor(root);
    if (ownedState(root, location.href) !== ownedState(root, state.committedURL)) {
      refresh(root, location.href, "restore");
    } else if (state.retry) {
      cancel(state);
      state.retry = null;
      setBusy(root, false);
      root.querySelector("[data-table-refresh-error]").hidden = true;
      const input = root.querySelector("[data-table-search-input]");
      if (input) input.value = input.defaultValue;
    }
  }
});

function enhance(root) {
  stateFor(root);
  root.dataset.tableEnhanced = "true";
}

document.addEventListener("tings-table-ready", event => {
  if (event.target.matches(selector)) enhance(event.target);
});
for (const root of document.querySelectorAll(selector + '[data-table-runtime-ready="true"]')) enhance(root);

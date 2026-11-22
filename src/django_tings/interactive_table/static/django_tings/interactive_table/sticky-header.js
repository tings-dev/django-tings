export function isEligibleTableStateClick(event) {
  return (
    event.button === 0 &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey &&
    !event.defaultPrevented
  );
}

export function createHorizontalTableOverflowController(root) {
  let scroller = null;
  let started = false;

  const sync = () => {
    if (!(scroller instanceof HTMLElement)) return;
    if (scroller.scrollWidth > scroller.clientWidth + 1) {
      scroller.removeAttribute("data-table-no-horizontal-overflow");
    } else {
      scroller.setAttribute("data-table-no-horizontal-overflow", "");
    }
  };

  const resizeObserver =
    typeof ResizeObserver === "function" ? new ResizeObserver(sync) : null;

  const teardown = () => {
    resizeObserver?.disconnect();
    scroller?.removeAttribute("data-table-no-horizontal-overflow");
    scroller = null;
  };

  const rebuild = () => {
    teardown();
    const nextScroller = root.querySelector(".interactive-table-scroll");
    const table = nextScroller?.querySelector(":scope > table");
    if (
      !(nextScroller instanceof HTMLElement) ||
      !(table instanceof HTMLElement)
    ) {
      return false;
    }
    scroller = nextScroller;
    if (resizeObserver === null) return true;
    sync();
    resizeObserver?.observe(scroller);
    resizeObserver?.observe(table);
    return true;
  };

  return {
    start() {
      if (started) return;
      started = true;
      rebuild();
    },
    rebuild,
    teardown,
  };
}

export function createStickyTableHeaderController(root) {
  const slot = root.querySelector("[data-table-sticky-header]");
  if (!(slot instanceof HTMLElement)) {
    return {
      start() {},
      rebuild() {
        return false;
      },
      teardown() {},
    };
  }

  const desktopMedia = window.matchMedia("(min-width: 48rem)");
  let active = null;
  let resizeFrame = 0;
  let resizeScheduled = false;
  let started = false;

  const restoreAttribute = (element, name, present, value) => {
    if (present) element.setAttribute(name, value);
    else element.removeAttribute(name);
  };

  const restoreSourceControls = (states) => {
    for (const state of states) {
      restoreAttribute(
        state.link,
        "aria-hidden",
        state.ariaHiddenPresent,
        state.ariaHidden,
      );
      restoreAttribute(
        state.link,
        "tabindex",
        state.tabindexPresent,
        state.tabindex,
      );
      restoreAttribute(
        state.link,
        "data-table-focus-key",
        state.focusKeyPresent,
        state.focusKey,
      );
      restoreAttribute(
        state.header,
        "aria-label",
        state.headerLabelPresent,
        state.headerLabel,
      );
    }
  };

  const stopResizeFrame = () => {
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame);
    resizeFrame = 0;
    resizeScheduled = false;
  };

  const resizeObserver =
    typeof ResizeObserver === "function"
      ? new ResizeObserver(() => scheduleGeometrySync())
      : null;

  const teardown = () => {
    stopResizeFrame();
    resizeObserver?.disconnect();
    if (active) {
      active.scroller.removeEventListener("scroll", active.syncScroll);
      restoreSourceControls(active.sourceStates);
    }
    active = null;
    slot.replaceChildren();
    slot.removeAttribute("data-table-sticky-active");
    slot.style.removeProperty("--table-sticky-header-height");
    slot.hidden = true;
  };

  const measureGeometry = () => {
    if (!active) return;
    const sourceCells = active.sourceHead.querySelectorAll("th");
    if (sourceCells.length !== active.columns.length) {
      throw new Error("Sticky table header columns changed");
    }
    const widths = Array.from(sourceCells, (cell) =>
      cell.getBoundingClientRect().width,
    );
    const height = active.sourceHead.getBoundingClientRect().height;
    const tableWidth = Math.max(
      active.sourceTable.scrollWidth,
      active.sourceTable.getBoundingClientRect().width,
    );
    if (
      !Number.isFinite(height) ||
      height <= 0 ||
      !Number.isFinite(tableWidth) ||
      tableWidth <= 0 ||
      widths.some((width) => !Number.isFinite(width) || width <= 0)
    ) {
      throw new Error("Sticky table header could not be measured");
    }
    active.columns.forEach((column, index) => {
      column.style.inlineSize = `${widths[index]}px`;
    });
    active.proxyTable.style.inlineSize = `${tableWidth}px`;
    slot.style.setProperty("--table-sticky-header-height", `${height}px`);
    active.syncScroll();
  };

  function scheduleGeometrySync() {
    if (resizeScheduled) return;
    resizeScheduled = true;
    resizeFrame = window.requestAnimationFrame(() => {
      resizeFrame = 0;
      resizeScheduled = false;
      try {
        measureGeometry();
      } catch {
        teardown();
      }
    });
  }

  const rebuild = () => {
    teardown();
    if (!desktopMedia.matches) return false;

    const scroller = root.querySelector(".interactive-table-scroll");
    const sourceTable = scroller?.querySelector(":scope > table");
    const sourceHead = sourceTable?.querySelector("thead");
    if (
      !(scroller instanceof HTMLElement) ||
      !(sourceTable instanceof HTMLElement) ||
      !(sourceHead instanceof HTMLElement)
    ) {
      return false;
    }

    const sourceCells = Array.from(sourceHead.querySelectorAll("th"));
    const sourceLinks = Array.from(
      sourceHead.querySelectorAll(
        'a[data-table-state-url][data-table-focus-key^="sort-desktop-"]',
      ),
    );
    const proxyTable = sourceTable.cloneNode(false);
    const proxyHead = sourceHead.cloneNode(true);
    const proxyCells = Array.from(proxyHead.querySelectorAll("th"));
    const proxyLinks = Array.from(
      proxyHead.querySelectorAll(
        'a[data-table-state-url][data-table-focus-key^="sort-desktop-"]',
      ),
    );
    if (
      !sourceCells.length ||
      sourceCells.length !== proxyCells.length ||
      sourceLinks.length !== proxyLinks.length
    ) {
      return false;
    }

    proxyTable.removeAttribute("id");
    proxyTable.className = `${sourceTable.className} table-sticky-header__table`;
    proxyTable.setAttribute("role", "presentation");
    for (const duplicateId of proxyHead.querySelectorAll("[id]")) {
      duplicateId.removeAttribute("id");
    }

    const columns = sourceCells.map(() => document.createElement("col"));
    const columnGroup = document.createElement("colgroup");
    columnGroup.append(...columns);
    const viewport = document.createElement("div");
    viewport.className = "table-sticky-header__viewport";
    proxyTable.append(columnGroup, proxyHead);
    viewport.append(proxyTable);

    const sourceStates = [];
    for (const proxyCell of proxyCells) {
      proxyCell.setAttribute("role", "presentation");
      for (const semanticAttribute of [
        "aria-label",
        "aria-sort",
        "headers",
        "scope",
      ]) {
        proxyCell.removeAttribute(semanticAttribute);
      }
      if (
        !proxyCell.querySelector(
          'a[data-table-state-url][data-table-focus-key^="sort-desktop-"]',
        )
      ) {
        proxyCell.setAttribute("aria-hidden", "true");
      }
    }

    for (let index = 0; index < sourceLinks.length; index += 1) {
      const sourceLink = sourceLinks[index];
      const proxyLink = proxyLinks[index];
      if (
        !(sourceLink instanceof HTMLAnchorElement) ||
        !(proxyLink instanceof HTMLAnchorElement)
      ) {
        return false;
      }
      const header = sourceLink.closest("th");
      const label = sourceLink.querySelector("span")?.textContent?.trim();
      if (!(header instanceof HTMLElement) || !label) return false;

      sourceStates.push({
        link: sourceLink,
        header,
        ariaHiddenPresent: sourceLink.hasAttribute("aria-hidden"),
        ariaHidden: sourceLink.getAttribute("aria-hidden") ?? "",
        tabindexPresent: sourceLink.hasAttribute("tabindex"),
        tabindex: sourceLink.getAttribute("tabindex") ?? "",
        focusKeyPresent: sourceLink.hasAttribute("data-table-focus-key"),
        focusKey: sourceLink.getAttribute("data-table-focus-key") ?? "",
        headerLabelPresent: header.hasAttribute("aria-label"),
        headerLabel: header.getAttribute("aria-label") ?? "",
      });
      proxyLink.removeAttribute("data-on:table-state-request");
      proxyLink.removeAttribute("data-indicator");
    }

    const syncScroll = () => {
      viewport.scrollLeft = scroller.scrollLeft;
    };
    scroller.addEventListener("scroll", syncScroll, { passive: true });
    active = {
      scroller,
      sourceTable,
      sourceHead,
      proxyTable,
      viewport,
      columns,
      sourceStates,
      syncScroll,
    };

    try {
      for (const state of sourceStates) {
        state.header.setAttribute("aria-label", state.headerLabel || state.link.querySelector("span").textContent.trim());
        state.link.setAttribute("aria-hidden", "true");
        state.link.setAttribute("tabindex", "-1");
        state.link.removeAttribute("data-table-focus-key");
      }
      slot.replaceChildren(viewport);
      measureGeometry();
      slot.hidden = false;
      slot.setAttribute("data-table-sticky-active", "");
      resizeObserver?.disconnect();
      resizeObserver?.observe(scroller);
      resizeObserver?.observe(sourceTable);
      return true;
    } catch {
      teardown();
      return false;
    }
  };

  const handleDesktopChange = () => {
    if (desktopMedia.matches) rebuild();
    else teardown();
  };

  const start = () => {
    if (started) return;
    started = true;
    desktopMedia.addEventListener("change", handleDesktopChange);
    rebuild();
    document.fonts?.ready.then(() => scheduleGeometrySync());
  };

  return {
    start,
    rebuild,
    teardown,
    dispose() {
      desktopMedia.removeEventListener("change", handleDesktopChange);
      teardown();
    },
  };
}

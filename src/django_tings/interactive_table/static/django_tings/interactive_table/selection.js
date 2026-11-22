// Mirrors desktop and card checkboxes for the same record.
export function restoreSelection(root, selected) {
  const bar = root.querySelector("[data-table-selection-bar]");
  if (!bar) return;
  const boxes = [...root.querySelectorAll("[data-table-row-select]")];
  boxes.forEach(box => { box.checked = selected.has(box.value); });
  const all = bar.querySelector("[data-table-select-page]");
  all.checked = boxes.length > 0 && boxes.every(box => box.checked);
  all.indeterminate = !all.checked && boxes.some(box => box.checked);
  const count = new Intl.NumberFormat(bar.lang).format(selected.size);
  bar.querySelector("[data-table-selection-count]").textContent = selected.size
    ? bar.dataset.selectionCountTemplate.replaceAll("{count}", count) : bar.dataset.selectionNone;
  for (const button of bar.querySelectorAll("[data-table-selection-clear], [data-table-selection-act]")) {
    button.disabled = !selected.size;
  }
}

export function changeSelection(root, selected, target) {
  const boxes = target.matches("[data-table-select-page]")
    ? root.querySelectorAll("[data-table-row-select]") : [target];
  for (const box of boxes) {
    if (target.checked) selected.add(box.value);
    else selected.delete(box.value);
  }
  restoreSelection(root, selected);
}

(function () {
    // -----------------------------------------------------------------------
    // Utility
    // -----------------------------------------------------------------------
    function escapeHtml(str) {
        return String(str == null ? "" : str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    // -----------------------------------------------------------------------
    // Cell renderers — keyed by the "renderer" field in column_defs
    // -----------------------------------------------------------------------
    // Correlating logs across sources only works if the timezone is explicit —
    // silently dropping the offset (as a naive substring(0, 19) would) makes
    // "10:22:01" ambiguous whenever the ingested files don't all share one tz.
    const timestampRenderer = p => {
        if (!p.value) return "";
        const datePart = p.value.substring(0, 19).replace("T", " ");
        const offsetMatch = p.value.slice(19).match(/Z|[+-]\d{2}:?\d{2}/);
        return offsetMatch ? `${datePart} ${offsetMatch[0]}` : datePart;
    };

    // Timestamp is the only field still rendered through this map — every
    // other field the grid used to show (category/status/ip/method/path/ua)
    // is detail-panel-only since the Splunk-style Timestamp+Event redesign.
    const RENDERERS = {
        timestamp: timestampRenderer,
    };

    // -----------------------------------------------------------------------
    // Filter-by-value icon, injected into every filterable cell
    // -----------------------------------------------------------------------
    // "raw" already backs free-text search, so a per-value filter on it adds nothing.
    const NOT_FILTERABLE = new Set(["raw"]);

    function filterIconHtml(field, value) {
        const escapedValue = escapeHtml(String(value));
        return `<button type="button" class="cell-filter-btn" data-filter-field="${escapeHtml(field)}" data-filter-value="${escapedValue}" title="Filter by ${escapedValue}" tabindex="-1">
            <svg viewBox="0 0 16 16" width="10" height="10" aria-hidden="true"><path d="M1 2h14l-5.5 6.5V14l-3-1.5V8.5L1 2z" fill="currentColor"/></svg>
        </button>`;
    }

    // -----------------------------------------------------------------------
    // Build AG Grid columnDefs from the server descriptor array
    // -----------------------------------------------------------------------
    function buildColumnDefs(serverDefs) {
        // Some server defs exist only to give a field a friendly label in
        // the detail panel (via buildLabelMap below) without cluttering the
        // grid with a low-signal column.
        return serverDefs.filter(d => d.showInGrid !== false).map(d => {
            const col = {
                field:      d.field,
                headerName: d.headerName,
            };
            if (d.width)        col.width        = d.width;
            if (d.flex)         col.flex         = d.flex;
            if (d.minWidth)     col.minWidth     = d.minWidth;
            if (d.type)         col.type         = d.type;
            if (d.pinned)       col.pinned       = d.pinned;
            if (d.tooltipField) col.tooltipField = d.tooltipField;
            // "raw" wraps and grows the row to fit its full content — the
            // whole point of the Event column is not losing text at a
            // glance, so it must accommodate the content instead of the
            // other way around (Splunk's event list works the same way).
            if (d.field === "raw") {
                col.wrapText   = true;
                col.autoHeight = true;
            }

            const innerRenderer = d.renderer && RENDERERS[d.renderer];
            const filterable    = !NOT_FILTERABLE.has(d.field);

            col.cellRenderer = p => {
                const inner = innerRenderer
                    ? innerRenderer(p)
                    : (p.value != null ? escapeHtml(String(p.value)) : "");
                if (!filterable || p.value === null || p.value === undefined || p.value === "") {
                    return inner;
                }
                return `<span class="cell-value">${inner}</span>${filterIconHtml(d.field, p.value)}`;
            };

            if (d.field === "raw") {
                col.cellStyle = { fontFamily: "monospace", fontSize: "11px", color: "#333", lineHeight: "1.5", padding: "6px 4px" };
                // overflow-wrap (not word-break: break-all) — only breaks a
                // word mid-character when it wouldn't fit on its own line,
                // instead of breaking eagerly wherever a line gets tight.
                Object.assign(col.cellStyle, { overflowWrap: "anywhere" });
            }
            return col;
        });
    }

    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------
    let searchTerms          = [];
    let currentPage          = 1;
    let currentProject       = null;
    let columnDefsFromServer = [];
    let esIsAlive            = true;
    let noDataInES           = false;
    const PAGE_SIZE          = 50;

    const pageShell      = document.getElementById('page-shell');
    const apiProjectsUrl = pageShell?.dataset.apiProjectsUrl || null;
    const apiSearchUrl   = pageShell?.dataset.apiSearchUrl || null;

    // -----------------------------------------------------------------------
    // Grid — starts with empty columnDefs; hydrated on first loadPage()
    // -----------------------------------------------------------------------
    const gridOptions = {
        columnDefs: [],
        rowData: [],
        defaultColDef: { resizable: true, sortable: false, filter: false },
        rowSelection: "single",
        onRowClicked: e => showDetail(e.data),
        pagination: true,
        paginationPageSize: PAGE_SIZE,
        suppressPaginationPanel: true,
        headerHeight: 36,
        rowHeight: 30,
        suppressCellFocus: true,
        enableCellTextSelection: true,
        animateRows: false,
    };

    const gridEl = document.getElementById("log-grid");
    const grid   = agGrid.createGrid(gridEl, gridOptions);

    // -----------------------------------------------------------------------
    // Project picker — custom dropdown: switch project, delete, or add one.
    // Replaces a native <select> because <option> can't host a delete icon.
    // -----------------------------------------------------------------------
    const projectPicker      = document.getElementById("project-picker");
    const projectPickerBtn   = document.getElementById("project-picker-toggle");
    const projectPickerLabel = document.getElementById("project-picker-label");
    const projectPickerMenu  = document.getElementById("project-picker-menu");
    const projectLabel       = document.getElementById("project-label");

    let knownProjects = [];

    function updateProjectLabel() {
        const text = currentProject || "All projects";
        projectLabel.textContent = text;
        projectPickerLabel.textContent = text;
    }

    function renderProjectPickerMenu() {
        const allItem =
            `<div class="project-picker-item${currentProject ? "" : " is-active"}" data-project="">
                <span class="ppi-name">All projects</span>
            </div>`;

        const projectItems = knownProjects.map(p => `
            <div class="project-picker-item${p === currentProject ? " is-active" : ""}" data-project="${escapeHtml(p)}">
                <span class="ppi-name">${escapeHtml(p)}</span>
                <button type="button" class="ppi-delete" data-delete-project="${escapeHtml(p)}" title="Delete project ${escapeHtml(p)}">&times;</button>
            </div>`
        ).join("");

        projectPickerMenu.innerHTML =
            allItem + projectItems +
            `<div class="project-picker-divider"></div>
             <div class="project-picker-add" id="project-picker-add">+ Add project</div>`;
    }

    function openProjectPicker() {
        renderProjectPickerMenu();
        projectPickerMenu.classList.remove("hidden");
        projectPickerBtn.setAttribute("aria-expanded", "true");
    }

    function closeProjectPicker() {
        projectPickerMenu.classList.add("hidden");
        projectPickerBtn.setAttribute("aria-expanded", "false");
    }

    projectPickerBtn.addEventListener("click", () => {
        if (projectPickerMenu.classList.contains("hidden")) {
            openProjectPicker();
        } else {
            closeProjectPicker();
        }
    });

    document.addEventListener("click", e => {
        if (!projectPicker.contains(e.target)) closeProjectPicker();
    });

    document.addEventListener("keydown", e => {
        if (e.key === "Escape") closeProjectPicker();
    });

    projectPickerMenu.addEventListener("click", e => {
        const deleteBtn = e.target.closest("[data-delete-project]");
        if (deleteBtn) {
            e.stopPropagation();
            closeProjectPicker();
            openDeleteProjectModal(deleteBtn.dataset.deleteProject);
            return;
        }

        const addRow = e.target.closest("#project-picker-add");
        if (addRow) {
            closeProjectPicker();
            openUploadModal();
            return;
        }

        const item = e.target.closest(".project-picker-item");
        if (item) {
            currentProject = item.dataset.project || null;
            searchTerms = [];
            searchInput.value = "";
            renderTags();
            updateProjectLabel();
            closeProjectPicker();
            loadPage(1);
        }
    });

    function loadProjects() {
        if (!apiProjectsUrl) return Promise.reject(new Error('Missing apiProjectsUrl'));
        return fetch(apiProjectsUrl, { cache: "no-store" })
            .then(r => r.json())
            .then(projects => {
                knownProjects = projects;
                if (currentProject && !projects.includes(currentProject)) {
                    currentProject = null;
                }
                if (!currentProject && projects.length === 1) {
                    currentProject = projects[0];
                }
                projectPicker.classList.remove("hidden");
                updateProjectLabel();
            })
            .catch(() => {
                // The picker still doubles as the entry point to add a
                // project, so keep it usable even if this fetch failed.
                projectPicker.classList.remove("hidden");
            });
    }

    // -----------------------------------------------------------------------
    // Reset the view after a project's data is gone — same as a fresh load.
    // -----------------------------------------------------------------------
    function afterProjectDeleted(deletedSlug) {
        if (currentProject === deletedSlug) {
            currentProject = null;
            searchTerms = [];
            searchInput.value = "";
            renderTags();
        }
        loadProjects().then(() => loadPage(1));
    }

    // -----------------------------------------------------------------------
    // Detail panel
    // -----------------------------------------------------------------------
    const detailPanel = document.getElementById("detail-panel");
    const detailTitle = document.getElementById("detail-title");
    const detailBody  = document.getElementById("detail-body");
    const SKIP_IN_DETAIL = new Set(["raw", "log_format", "project"]);

    function buildLabelMap(defs) {
        const map = {};
        for (const d of defs) map[d.field] = d.headerName;
        return map;
    }

    function showDetail(data) {
        const labels = buildLabelMap(columnDefsFromServer);
        const rows = Object.entries(data)
            .filter(([k, v]) => !SKIP_IN_DETAIL.has(k) && v !== null && v !== undefined && v !== "")
            .map(([k, v]) => {
                const label  = labels[k] || k;
                const display = typeof v === "object" ? JSON.stringify(v) : String(v);
                return `<tr>
                    <td class="dp-key">${escapeHtml(label)}</td>
                    <td class="dp-val">${escapeHtml(display)}</td>
                </tr>`;
            }).join("");

        const ts = data.timestamp ? timestampRenderer({ value: data.timestamp }) : "";
        detailTitle.textContent = ts ? `Event — ${ts}` : "Event detail";

        // The original log line is the ground truth for an investigation —
        // show it verbatim above the parsed fields, not folded into the
        // generic key/value table where it'd be easy to overlook.
        const rawBlock = data.raw
            ? `<pre class="dp-raw">${escapeHtml(data.raw)}</pre>`
            : "";
        detailBody.innerHTML = `${rawBlock}<table class="dp-table"><tbody>${rows}</tbody></table>`;
        detailPanel.style.height = Math.round(window.innerHeight * 0.45) + "px";
        detailPanel.classList.add("is-open");
    }

    function hideDetail() {
        detailPanel.style.height = "0";
        detailPanel.classList.remove("is-open");
        grid.deselectAll();
    }

    document.getElementById("detail-close").addEventListener("click", hideDetail);

    // -----------------------------------------------------------------------
    // Empty state
    // -----------------------------------------------------------------------
    const emptyState = document.getElementById("empty-state");
    const emptyTitle = document.getElementById("empty-title");
    const emptySub   = document.getElementById("empty-subtitle");
    const emptyCta   = document.getElementById("empty-cta");

    function showEmptyState(isNoData) {
        noDataInES = isNoData;
        if (isNoData) {
            emptyTitle.textContent = "No logs ingested yet";
            emptySub.textContent   = "Upload a log file to start exploring your traces.";
            emptyCta.style.display = "";
        } else {
            emptyTitle.textContent = `No results for ${searchTerms.map(t => `\u201c${escapeHtml(t)}\u201d`).join(" + ")}`;
            emptySub.textContent   = "Try a different search term.";
            emptyCta.style.display = "none";
        }
        emptyState.classList.add("is-visible");
        gridEl.classList.add("is-hidden");
        setToolbarDisabled(isNoData);
    }

    function hideEmptyState() {
        emptyState.classList.remove("is-visible");
        gridEl.classList.remove("is-hidden");
        setToolbarDisabled(false);
    }

    emptyCta.addEventListener('click', function () {
        openUploadModal();
    });

    // -----------------------------------------------------------------------
    // Pagination
    // -----------------------------------------------------------------------
    const resultInfo  = document.getElementById("result-info");
    const pagerInline = document.getElementById("pager-inline");
    const formatBadge = document.getElementById("format-badge");

    function renderPagination(total, page, totalPages) {
        if (total === 0) {
            resultInfo.textContent = "No results";
            pagerInline.innerHTML = "";
            return;
        }

        resultInfo.textContent =
            `${total.toLocaleString()} entr${total === 1 ? "y" : "ies"} · page ${page} of ${totalPages}`;

        if (totalPages <= 1) {
            pagerInline.innerHTML = "";
            return;
        }

        const prevHtml = page > 1
            ? `<a href="#" class="btn btn-xs btn-default" data-p="${page - 1}">&larr;</a>`
            : `<span class="btn btn-xs btn-default disabled">&larr;</span>`;
        const nextHtml = page < totalPages
            ? `<a href="#" class="btn btn-xs btn-default" data-p="${page + 1}">&rarr;</a>`
            : `<span class="btn btn-xs btn-default disabled">&rarr;</span>`;

        pagerInline.innerHTML = prevHtml + nextHtml;
        pagerInline.querySelectorAll("a[data-p]").forEach(a => {
            a.addEventListener("click", e => {
                e.preventDefault();
                loadPage(+a.dataset.p);
            });
        });
    }

    // -----------------------------------------------------------------------
    // Data loading
    // -----------------------------------------------------------------------
    function showEsDownBanner() {
        hideEmptyState();
        grid.setGridOption("rowData", []);
        hideDetail();
        pagerInline.innerHTML = "";
        resultInfo.innerHTML =
            '<span style="color:#d9534f;font-weight:600;">&#9679; Elasticsearch is unreachable — searches are paused.</span>';
        setToolbarDisabled(true);
    }

    function loadPage(page) {
        if (!esIsAlive) {
            showEsDownBanner();
            return;
        }
        currentPage = page;
        const url = new URL(apiSearchUrl, window.location.origin);
        searchTerms.forEach(t => url.searchParams.append("q", t));
        url.searchParams.set("page", page);
        url.searchParams.set("page_size", PAGE_SIZE);
        if (currentProject) url.searchParams.set("project", currentProject);

        fetch(url)
            .then(r => {
                if (r.status === 503) {
                    esIsAlive = false;
                    showEsDownBanner();
                    return null;
                }
                return r.json();
            })
            .then(data => {
                if (!data) return;

                if (data.total === 0) {
                    hideDetail();
                    showEmptyState(searchTerms.length === 0);
                    formatBadge.style.display = "none";
                    resultInfo.textContent = searchTerms.length
                        ? `No results for ${searchTerms.map(t => `\u201c${escapeHtml(t)}\u201d`).join(" + ")}`
                        : "";
                    pagerInline.innerHTML = "";
                    return;
                }

                hideEmptyState();
                if (data.column_defs && data.column_defs.length) {
                    columnDefsFromServer = data.column_defs;
                    grid.setGridOption("columnDefs", buildColumnDefs(columnDefsFromServer));
                }
                grid.setGridOption("rowData", data.hits);
                hideDetail();

                if (data.format_label) {
                    formatBadge.textContent = data.format_label;
                    formatBadge.style.display = "";
                } else {
                    formatBadge.style.display = "none";
                }

                renderPagination(data.total, data.page, data.total_pages);
            })
            .catch(() => {
                showEsDownBanner();
            });
    }

    // -----------------------------------------------------------------------
    // Search controls
    // -----------------------------------------------------------------------
    const searchInput   = document.getElementById("search-input");
    const searchBtn     = document.getElementById("search-btn");
    const searchToolbar = document.getElementById("search-toolbar");
    const filterTags    = document.getElementById("filter-tags");

    function setToolbarDisabled(disabled) {
        searchToolbar.classList.toggle("is-disabled", disabled);
        filterTags.classList.toggle("is-disabled", disabled);
        searchInput.disabled = disabled;
        searchBtn.disabled   = disabled;
    }

    function renderTags() {
        const tagHtml = searchTerms.map((t, i) =>
            `<span class="filter-tag">${escapeHtml(t)}<button class="filter-tag-remove" data-i="${i}" title="Remove filter">&times;</button></span>`
        ).join("");
        const clearHtml = searchTerms.length
            ? `<button class="filter-clear-all">Clear all</button>`
            : "";
        filterTags.innerHTML = tagHtml + clearHtml;

        filterTags.querySelectorAll(".filter-tag-remove").forEach(btn => {
            btn.addEventListener("click", () => {
                searchTerms.splice(+btn.dataset.i, 1);
                renderTags();
                loadPage(1);
            });
        });
        const clearAllBtn = filterTags.querySelector(".filter-clear-all");
        if (clearAllBtn) {
            clearAllBtn.addEventListener("click", () => {
                searchTerms = [];
                renderTags();
                loadPage(1);
            });
        }
    }

    function doSearch() {
        if (noDataInES) return;
        const val = searchInput.value.trim();
        if (!val) {
            searchInput.classList.add("is-invalid");
            resultInfo.textContent = "Search term cannot be empty";
            resultInfo.classList.add("result-info-error");
            return;
        }
        searchInput.classList.remove("is-invalid");
        resultInfo.classList.remove("result-info-error");
        if (!searchTerms.includes(val)) {
            searchTerms.push(val);
        }
        searchInput.value = "";
        renderTags();
        loadPage(1);
    }

    searchBtn.addEventListener("click", doSearch);
    searchInput.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
    searchInput.addEventListener("input", () => {
        if (searchInput.classList.contains("is-invalid")) {
            searchInput.classList.remove("is-invalid");
            resultInfo.textContent = "";
            resultInfo.classList.remove("result-info-error");
        }
    });

    // -----------------------------------------------------------------------
    // Click-to-filter: the hover icon injected by buildColumnDefs()
    // -----------------------------------------------------------------------
    function addFieldFilter(field, value) {
        if (noDataInES) return;
        const term = `${field}:${value}`;
        if (searchTerms.includes(term)) return;
        searchTerms.push(term);
        renderTags();
        loadPage(1);
    }

    // Capture phase: must run before ag-grid's own row-click (detail panel)
    // listener, which fires on bubble and would otherwise still open on this click.
    gridEl.addEventListener("click", e => {
        const btn = e.target.closest(".cell-filter-btn");
        if (!btn) return;
        e.stopPropagation();
        addFieldFilter(btn.dataset.filterField, btn.dataset.filterValue);
    }, true);

    // -----------------------------------------------------------------------
    // React to health-check events emitted by base.html
    // -----------------------------------------------------------------------
    document.addEventListener("esStatusChange", e => {
        const wasAlive = esIsAlive;
        esIsAlive = e.detail.state === "alive";

        if (!esIsAlive) {
            showEsDownBanner();
        } else if (!wasAlive) {
            loadPage(currentPage);
        }
    });

    const uploadModal      = document.getElementById('upload-modal');
    const closeUploadBtns  = [
      document.querySelector('.upload-modal-close'),
      document.getElementById('upload-cancel')
    ].filter(Boolean);
    const dropzone         = document.querySelector('[data-dropzone]');
    const fileInput        = document.getElementById('log_file') || document.querySelector('input[type="file"]');
    const selectFileBtn    = document.getElementById('upload-select-btn');
    const clearFileBtn     = document.getElementById('upload-clear-btn');
    const fileMeta         = document.getElementById('upload-file-meta');

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    function assignFilesToInput(input, files) {
      if (!input || !files) return;
      if (typeof DataTransfer === 'function') {
        const dt = new DataTransfer();
        Array.from(files).forEach(file => dt.items.add(file));
        input.files = dt.files;
      } else if (typeof input.files !== 'undefined') {
        input.files = files;
      }
    }

    function setFilePreview(file) {
      if (!fileMeta) return;
      if (!file) {
        fileMeta.textContent = 'No file selected.';
        fileMeta.classList.remove('upload-file-meta--valid');
        fileMeta.classList.add('upload-file-meta--empty');
        if (clearFileBtn) clearFileBtn.classList.add('hidden');
        return;
      }
      const size = file.size < 1024 ? `${file.size} B`
        : file.size < 1024 * 1024 ? `${(file.size / 1024).toFixed(1)} KB`
        : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
      fileMeta.textContent = `${file.name} · ${size}`;
      fileMeta.classList.remove('upload-file-meta--empty');
      fileMeta.classList.add('upload-file-meta--valid');
      if (clearFileBtn) clearFileBtn.classList.remove('hidden');
    }

    function openUploadModal() {
      if (!uploadModal) return;
      uploadModal.classList.add('is-visible');
      uploadModal.setAttribute('aria-hidden', 'false');
    }

    function closeUploadModal() {
      if (!uploadModal) return;
      uploadModal.classList.remove('is-visible');
      uploadModal.setAttribute('aria-hidden', 'true');
    }

    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
      uploadForm.addEventListener('submit', function () {
        const overlay = document.getElementById('upload-overlay');
        if (overlay) overlay.classList.add('is-visible');
      });
    }

    closeUploadBtns.forEach(btn => btn.addEventListener('click', closeUploadModal));
    if (uploadModal) {
      uploadModal.addEventListener('click', function (event) {
        if (event.target === uploadModal) {
          closeUploadModal();
        }
      });
    }

    if (selectFileBtn) {
      selectFileBtn.addEventListener('click', function () {
        if (fileInput) fileInput.click();
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', function () {
        setFilePreview(this.files && this.files[0]);
      });
    }

    if (clearFileBtn) {
      clearFileBtn.addEventListener('click', function () {
        if (!fileInput) return;
        fileInput.value = '';
        if (typeof DataTransfer === 'function') {
          const dt = new DataTransfer();
          fileInput.files = dt.files;
        }
        setFilePreview(null);
      });
    }

    if (dropzone) {
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
      });

      dropzone.addEventListener('dragover', function () {
        dropzone.classList.add('drag-over');
      });

      dropzone.addEventListener('dragleave', function () {
        dropzone.classList.remove('drag-over');
      });

      dropzone.addEventListener('drop', function (event) {
        dropzone.classList.remove('drag-over');
        const files = event.dataTransfer.files;
        if (!files || files.length === 0) return;
        assignFilesToInput(fileInput, files);
        setFilePreview(files[0]);
      });
    }

    // -----------------------------------------------------------------------
    // Delete-project confirmation modal — requires typing the exact slug,
    // since this permanently deletes the project's log data from ES.
    // -----------------------------------------------------------------------
    const deleteModal         = document.getElementById('delete-project-modal');
    const deleteModalName     = document.getElementById('delete-project-name');
    const deleteModalEcho     = document.getElementById('delete-project-slug-echo');
    const deleteModalInput    = document.getElementById('delete-project-input');
    const deleteModalConfirm  = document.getElementById('delete-project-confirm-btn');
    const deleteModalCancel   = document.getElementById('delete-project-cancel');
    const deleteModalCloseBtn = document.querySelector('.confirm-modal-close');
    const deleteModalError    = document.getElementById('delete-project-error');

    let pendingDeleteSlug = null;

    function openDeleteProjectModal(slug) {
        if (!deleteModal) return;
        pendingDeleteSlug = slug;
        deleteModalName.textContent = slug;
        deleteModalEcho.textContent = slug;
        deleteModalInput.value = '';
        deleteModalConfirm.disabled = true;
        deleteModalConfirm.textContent = 'Delete project';
        deleteModalError.classList.add('hidden');
        deleteModal.classList.add('is-visible');
        deleteModal.setAttribute('aria-hidden', 'false');
        deleteModalInput.focus();
    }

    function closeDeleteProjectModal() {
        if (!deleteModal) return;
        pendingDeleteSlug = null;
        deleteModal.classList.remove('is-visible');
        deleteModal.setAttribute('aria-hidden', 'true');
    }

    if (deleteModalInput) {
        deleteModalInput.addEventListener('input', () => {
            deleteModalConfirm.disabled = deleteModalInput.value !== pendingDeleteSlug;
        });
    }
    if (deleteModalCancel) deleteModalCancel.addEventListener('click', closeDeleteProjectModal);
    if (deleteModalCloseBtn) deleteModalCloseBtn.addEventListener('click', closeDeleteProjectModal);
    if (deleteModal) {
        deleteModal.addEventListener('click', event => {
            if (event.target === deleteModal) closeDeleteProjectModal();
        });
    }

    if (deleteModalConfirm) {
        deleteModalConfirm.addEventListener('click', () => {
            if (!pendingDeleteSlug || deleteModalInput.value !== pendingDeleteSlug) return;
            const slug = pendingDeleteSlug;
            deleteModalConfirm.disabled = true;
            deleteModalConfirm.textContent = 'Deleting…';
            deleteModalError.classList.add('hidden');

            fetch(`${apiProjectsUrl}/${encodeURIComponent(slug)}`, { method: 'DELETE' })
                .then(r => r.json().then(body => ({ ok: r.ok, body })))
                .then(({ ok, body }) => {
                    if (!ok) throw new Error(body.error || 'Delete failed');
                    closeDeleteProjectModal();
                    afterProjectDeleted(slug);
                })
                .catch(err => {
                    deleteModalConfirm.disabled = false;
                    deleteModalConfirm.textContent = 'Delete project';
                    deleteModalError.textContent = err.message || 'Could not delete the project.';
                    deleteModalError.classList.remove('hidden');
                });
        });
    }

    loadProjects();
    loadPage(1);
})();

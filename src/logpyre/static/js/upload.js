(function () {
    const input = document.getElementById("log_file");
    if (!input) return;

    input.addEventListener("change", function () {
        const preview = document.getElementById("file-preview");
        const nameEl  = document.getElementById("file-preview-name");
        const sizeEl  = document.getElementById("file-preview-size");
        const file = this.files && this.files[0];
        if (!file) {
            preview.style.display = "none";
            return;
        }
        nameEl.textContent = file.name;
        sizeEl.textContent = window.Logpyre.formatBytes(file.size);
        preview.style.display = "block";
    });

    const form = input.closest("form");
    if (form) {
        form.addEventListener("submit", () => window.Logpyre.showUploadOverlay());
    }

    const projectInput = document.getElementById("project");
    if (!projectInput) return;

    const slugPattern = /^[a-z][a-z0-9_-]*$/;
    const hint = document.createElement("span");
    hint.className = "help-block";
    hint.style.display = "none";
    hint.textContent = "Only lowercase letters, digits, hyphens and underscores. Must start with a letter.";
    if (projectInput.parentNode) projectInput.parentNode.appendChild(hint);

    projectInput.addEventListener("input", function () {
        const val = this.value;
        const formGroup = this.closest(".form-group");
        const invalid = val !== "" && !slugPattern.test(val);
        const valid   = val !== "" && slugPattern.test(val);
        if (formGroup) {
            formGroup.classList.toggle("has-error", invalid);
            formGroup.classList.toggle("has-success", valid);
        }
        hint.style.display = invalid ? "" : "none";
    });
})();

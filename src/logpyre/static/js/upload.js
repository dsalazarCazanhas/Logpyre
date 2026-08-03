(function () {
    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    var input = document.getElementById('log_file');
    if (!input) return;

    input.addEventListener('change', function () {
        var preview = document.getElementById('file-preview');
        var nameEl  = document.getElementById('file-preview-name');
        var sizeEl  = document.getElementById('file-preview-size');
        var file = this.files && this.files[0];
        if (!file) {
            preview.style.display = 'none';
            return;
        }
        nameEl.textContent = file.name;
        sizeEl.textContent = formatBytes(file.size);
        preview.style.display = 'block';
    });

    var form = input.closest('form');
    if (form) {
        form.addEventListener('submit', function () {
            var overlay = document.getElementById('upload-overlay');
            if (overlay) overlay.classList.add('is-visible');
        });
    }

    var projectInput = document.getElementById('project');
    if (!projectInput) return;

    var slugPattern = /^[a-z][a-z0-9_-]*$/;
    var hint = document.createElement('span');
    hint.className = 'help-block';
    hint.style.display = 'none';
    hint.textContent = 'Only lowercase letters, digits, hyphens and underscores. Must start with a letter.';
    if (projectInput.parentNode) projectInput.parentNode.appendChild(hint);

    projectInput.addEventListener('input', function () {
        var val = this.value;
        var formGroup = this.closest('.form-group');
        var invalid = val !== '' && !slugPattern.test(val);
        var valid   = val !== '' && slugPattern.test(val);
        if (formGroup) {
            formGroup.classList.toggle('has-error', invalid);
            formGroup.classList.toggle('has-success', valid);
        }
        hint.style.display = invalid ? '' : 'none';
    });
})();

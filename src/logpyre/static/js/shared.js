// Shared helpers loaded before both upload.js and index.js — each has its
// own upload form/file input and used to carry a byte-for-byte copy of this
// logic. No bundler in this project, so this is a plain global namespace
// rather than an ES module import.
window.Logpyre = (function () {
    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function showUploadOverlay() {
        const overlay = document.getElementById("upload-overlay");
        if (overlay) overlay.classList.add("is-visible");
    }

    return { formatBytes, showUploadOverlay };
})();

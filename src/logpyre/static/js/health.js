(function () {
    var badge = document.getElementById("es-status");
    if (!badge) return;

    var label = badge.querySelector(".es-label");
    var healthUrl = badge.dataset.healthUrl;
    var POLL_INTERVAL = 15000;

    function setState(state, text) {
        badge.className = "es-status es-status--" + state;
        if (label) {
            label.textContent = text;
        }
        document.dispatchEvent(new CustomEvent("esStatusChange", { detail: { state: state } }));
    }

    function poll() {
        fetch(healthUrl, { method: "GET", cache: "no-store" })
            .then(function (r) {
                if (r.ok) {
                    setState("alive", "alive");
                } else {
                    setState("down", "down");
                }
            })
            .catch(function () {
                setState("down", "down");
            });
    }

    poll();
    setInterval(poll, POLL_INTERVAL);
})();

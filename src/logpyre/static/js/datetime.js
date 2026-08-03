(function () {
    var timeEl = document.getElementById('page-time');
    if (!timeEl) return;

    function pad(n) {
        return String(n).padStart(2, '0');
    }

    function formatLocal(dt) {
        var day = pad(dt.getDate());
        var month = pad(dt.getMonth() + 1);
        var year = dt.getFullYear();
        var hours = pad(dt.getHours());
        var minutes = pad(dt.getMinutes());
        return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
    }

    function updateClock() {
        var now = new Date();
        timeEl.textContent = formatLocal(now);
    }

    updateClock();
    setInterval(updateClock, 60000);
})();

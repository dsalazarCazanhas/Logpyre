(function () {
    var toast = document.querySelector('.logpyre-toast');
    if (!toast) return;

    function dismissToast() {
        toast.style.transition = 'opacity 0.4s, transform 0.4s';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(12px)';
        setTimeout(function () { toast.remove(); }, 420);
    }

    var closeButton = toast.querySelector('.logpyre-toast-close');
    if (closeButton) {
        closeButton.addEventListener('click', dismissToast);
    }

    setTimeout(dismissToast, 4000);
})();

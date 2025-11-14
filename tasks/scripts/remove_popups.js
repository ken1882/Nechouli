(function () {
    const INTERVAL = 1000;
    const selectors = [
        ".ant-modal-root"
    ]
    const intervalId = setInterval(() => {
        document.querySelectorAll(selectors.join(",")).forEach(el => el.remove());
    }, INTERVAL);
    setTimeout(() => clearInterval(intervalId), 30000);
})();

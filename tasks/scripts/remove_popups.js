(function () {
    const INTERVAL = 1000;
    const selectors = [
        ".ant-modal-root",
        ".nl-ad-top",
        ".nl-ad-left",
        ".nl-ad-right",
    ]
    const intervalId = setInterval(() => {
        document.querySelectorAll(selectors.join(",")).forEach(el => el.remove());
    }, INTERVAL);
    setTimeout(() => clearInterval(intervalId), 30000);
})();

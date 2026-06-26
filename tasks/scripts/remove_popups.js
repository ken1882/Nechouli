(function () {
    const INTERVAL = 1000;
    const LIFETIME = 300000;
    const close_selectors = [
        "#ta-ab-close",
        ".ta-ab-close",
    ]
    const selectors = [
        "#ta-ab-overlay",
        ".ta-ab-overlay",
        ".ant-modal-root",
        ".nl-ad-top",
        ".nl-ad-left",
        ".nl-ad-right",
    ]
    const removePopups = () => {
        document.querySelectorAll(close_selectors.join(",")).forEach(el => el.click());
        document.querySelectorAll(selectors.join(",")).forEach(el => el.remove());
    };

    removePopups();
    const intervalId = setInterval(removePopups, INTERVAL);
    setTimeout(() => clearInterval(intervalId), LIFETIME);
})();

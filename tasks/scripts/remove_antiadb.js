
(function () {
    const INTERVAL = 1000;

    const intervalId = setInterval(() => {
    const alerts = Array.from(document.querySelectorAll("h3")).filter(h3 =>
        h3.textContent.includes("🚨")
    );

    if (alerts.length === 0) return;

    for (const h3 of alerts) {
        let node = h3;
        while (node && node.parentElement && node.parentElement.tagName !== "BODY") {
            node = node.parentElement;
        }

        if (node && node.parentElement === document.body) {
            node.remove();
        }
    }

    // stop after the first match
    if (alerts.length > 0) {
        clearInterval(intervalId);
    }
    }, INTERVAL);
})();

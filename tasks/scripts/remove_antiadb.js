
(function () {
    const INTERVAL = 1000;
    const intervalId = setInterval(() => {
        const alerts = Array.from(document.querySelectorAll("h3")).filter(h3 =>
            h3.textContent.includes("🚨")
        );

        for (const h3 of alerts) {
            let node = h3;
            while (node && node.parentElement && node.parentElement.tagName !== "BODY") {
                node = node.parentElement;
            }

            if (node && node.parentElement === document.body) {
                node.remove();
            }
        }

        const popups = document.querySelectorAll(".ta-ab-overlay");
        for (const popup of popups) {
            popup.remove();
        }

        // stop after 1 minute
        setTimeout(() => clearInterval(intervalId), 60000);
    }, INTERVAL);
})();

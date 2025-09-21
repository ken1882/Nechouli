(function () {
    const INTERVAL = 1000;

    const intervalId = setInterval(() => {
    const popup = document.getElementById("TVWChapterBoostPopup");
    const overlay = document.getElementById("navpopupshade__2020");
    if(!popup && !overlay) return;
    if (popup) { popup.remove(); }
    if (overlay) { overlay.remove(); }
    clearInterval(intervalId);
    }, INTERVAL);
})();

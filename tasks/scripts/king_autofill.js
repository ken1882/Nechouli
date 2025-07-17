(function () {
    'use strict';

    // Helpers to read/write from localStorage
    function getStoredBool(key, defaultValue) {
        const value = localStorage.getItem(key);
        return value === null ? defaultValue : value === 'true';
    }

    function setStoredBool(key, value) {
        localStorage.setItem(key, value ? 'true' : 'false');
    }

    // Settings
    let A_JOKE = getStoredBool('np_kswhaj', true);  // Use avatar joke
    let RF_RD = getStoredBool('np_kswhar', true);   // Randomize on refresh

    // rando function
    const newr = (l) => 1 + Math.floor(Math.random() * (l - 1));
    const AV = [3, 8, 6, 1, 39, 118, 1, 32, 1, 143];
    const grump = window.location.href.includes('/grumpyking.phtml');

    const rdgn = () => {
        document.querySelectorAll('.form-container__2021 select').forEach((j, idx) => {
            if (j.id[0] === 'q') {
                if (A_JOKE === true) {
                    j.selectedIndex = grump ? AV[idx] : newr(j.length);
                } else {
                    j.selectedIndex = newr(j.length);
                }
            } else {
                j.selectedIndex = newr(j.length);
            }
        });
    };

    // Randomize on page load
    window.addEventListener('load', () => {
        if (RF_RD) rdgn();
    });

    // Checkbox: Use avatar joke (only on Grumpy King page)
    if (grump) {
        const useAVJ = document.createElement('input');
        const useAVJLabel = document.createElement('label');
        useAVJLabel.innerText = "Use avatar joke";
        useAVJ.type = "checkbox";
        useAVJ.checked = A_JOKE;
        useAVJ.addEventListener('change', () => {
            setStoredBool("np_kswhaj", useAVJ.checked);
        });
        useAVJLabel.prepend(useAVJ);
    }

    rdgn();
})();

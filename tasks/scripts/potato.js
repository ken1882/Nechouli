(function() {
    'use strict';

    const imageUrls = [
        'https://images.neopets.com/medieval/potato1.gif',
        'https://images.neopets.com/medieval/potato2.gif',
        'https://images.neopets.com/medieval/potato3.gif',
        'https://images.neopets.com/medieval/potato4.gif'
    ];

    function countImages() {
        let totalCount = 0;
        let images = document.querySelectorAll('img');

        images.forEach((img) => {
            if (imageUrls.includes(img.src)) {
                totalCount++;
            }
        });

        // Calculate the delay based on the total count
        const finalDelay = totalCount * 30;

        // Ensure the overlay is updated after the calculated delay
        setTimeout(() => {
            updateOverlay(totalCount);
        }, finalDelay);
    }

    function updateOverlay(count) {
        let message = count > 0
            ? `The solution to the puzzle is: ${count}`
            : `No potatoes found.`;

        let overlay = document.querySelector('#potato-counter-overlay');
        if (!overlay) {
            // Create the overlay if it doesn't exist
            overlay = document.createElement('div');
            overlay.id = 'potato-counter-overlay';
            overlay.style.position = 'absolute';
            overlay.style.top = '50px'; // Adjust top to be closer to the button
            overlay.style.right = '10px'; // Adjust right to be closer to the button
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
            overlay.style.color = 'white';
            overlay.style.padding = '10px';
            overlay.style.borderRadius = '5px';
            overlay.style.zIndex = '1000';
            overlay.style.fontSize = '16px';
            overlay.style.maxWidth = '300px'; // Optional: set a max width for the overlay
            document.body.appendChild(overlay);
        }
        overlay.textContent = message;
    }

    countImages();
})();
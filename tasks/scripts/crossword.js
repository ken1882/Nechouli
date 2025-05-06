(async function() {
    'use strict';

    console.log("Neopets Crossword script is running...");

    // Fetch the JSON data
    console.log("Fetching JSON data...");
    let data;
    const clueMap = new Map(); // Create a map to store clues and answers

    try {
        const response = await fetch('https://raw.githubusercontent.com/unoriginality786/NeopetsFaerieCrosswordJSON/refs/heads/main/QuestionsAnswers');
        data = await response.json();
        console.log("JSON data fetched successfully:", data);

        // Map clues to speed up search functionality
        clueMap.clear();
        data.clues.forEach(entry => {
            const normalizedClue = (entry.clue || entry.question || "").toLowerCase().trim();
            if (normalizedClue) {
                clueMap.set(normalizedClue, entry.answer);
                console.log(`Loaded clue: "${normalizedClue}" -> Answer: "${entry.answer}"`);
            }
        });
        console.log("Clue map loaded:", [...clueMap.entries()]); // Log all clues
    } catch (error) {
        console.error("Error fetching JSON data:", error);
        return;
    }

    // Function to modify clue links
    function modifyClueLinks() {
        const clues = document.querySelectorAll('A[href^="javascript:;"]');
        console.log("Clue links found:", clues.length);

        if (clues.length === 0) {
            console.warn("No clue links found.");
            return;
        }

        clues.forEach((clue) => {
            clue.addEventListener('click', (event) => {
                event.preventDefault();
                const clueText = clue.innerText.trim().replace(/^\d+\.\s*/, '');
                console.log("Cleaned Clue Text:", clueText);

                // Find the corresponding answer using the clueMap
                const normalizedClickedClue = clueText.toLowerCase().trim();
                const answer = clueMap.get(normalizedClickedClue) || 'Not found';
                console.log(`Setting x_word to: ${answer}`);

                // Set the answer or log unable to find answer
                const xWordInput = document.querySelector('input[name="x_word"]');
                if (xWordInput) {
                    xWordInput.value = answer;
                } else {
                    console.error("x_word input not found.");
                }
            });
        });
    }

    // Use Mutation Observer to detect changes in the DOM
    const observer = new MutationObserver(() => {
        modifyClueLinks();
    });

    // Start observing changes in the body
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Initial call to modify clue links on page load
    window.addEventListener('load', () => {
        console.log("Page loaded, modifying clue links...");
        modifyClueLinks();
    });
})();

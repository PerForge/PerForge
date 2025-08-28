document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;

    // This function updates the icon based on the theme class on the body.
    const updateIcon = () => {
        const themeIcon = document.getElementById('themeIcon'); // Get the icon fresh each time
        if (!themeIcon) return;

        if (body.classList.contains('light-theme')) {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
        } else {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
        }
    };

    // The inline script in base-fullscreen.html sets the initial theme class.
    // We just need to set the initial icon state to match.
    updateIcon();

    // Use event delegation on the document to handle the click
    document.addEventListener('click', (event) => {
        // Check if the clicked element or its parent is the theme switcher button
        const themeSwitcher = event.target.closest('#themeSwitcher');

        if (themeSwitcher) {
            // Toggle the theme class on the body
            body.classList.toggle('light-theme');

            // Determine the new theme and save it to localStorage
            const newTheme = body.classList.contains('light-theme') ? 'light' : 'dark';
            localStorage.setItem('theme', newTheme);

            // Update the icon to reflect the new theme
            updateIcon();

            // Notify listeners (e.g., charts) that theme has changed
            try {
                document.dispatchEvent(new CustomEvent('theme:changed', { detail: { theme: newTheme } }));
            } catch (e) {
                // no-op if CustomEvent is not supported
            }
        }
    });
});

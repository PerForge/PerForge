document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.getElementById('themeSwitcher');
    const themeIcon = document.getElementById('themeIcon');
    const body = document.body;

    // This function updates the icon based on the theme class on the body.
    const updateIcon = () => {
        if (body.classList.contains('light-theme')) {
            if (themeIcon) themeIcon.classList.replace('fa-sun', 'fa-moon');
        } else {
            if (themeIcon) themeIcon.classList.replace('fa-moon', 'fa-sun');
        }
    };

    // The inline script in base-fullscreen.html sets the initial theme class.
    // We just need to set the initial icon state to match.
    updateIcon();

    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            // Toggle the theme class on the body
            body.classList.toggle('light-theme');
            
            // Determine the new theme and save it to localStorage
            const newTheme = body.classList.contains('light-theme') ? 'light' : 'dark';
            localStorage.setItem('theme', newTheme);

            // Update the icon to reflect the new theme
            updateIcon();
        });
    }
});

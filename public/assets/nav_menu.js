/**
 * Hamburger Navigation JS
 */
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('hamburger-btn');
    const drawer = document.getElementById('nav-drawer');
    const overlay = document.getElementById('nav-overlay');
    const links = document.querySelectorAll('.nav-link');

    if (!btn || !drawer || !overlay) {
        console.warn('[NAV] Navigation elements not found');
        return;
    }

    // Toggle Menu
    const toggleMenu = () => {
        const isOpen = drawer.classList.contains('open');
        if (isOpen) {
            drawer.classList.remove('open');
            overlay.classList.remove('visible');
            btn.innerHTML = '☰';
            document.body.style.overflow = ''; // Restore scroll
        } else {
            drawer.classList.add('open');
            overlay.classList.add('visible');
            btn.innerHTML = '✕';
            document.body.style.overflow = 'hidden'; // Prevent scroll
        }
    };

    btn.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', toggleMenu);

    // Highlight active link
    const currentPath = window.location.pathname;
    const currentSearch = window.location.search;

    links.forEach(link => {
        const page = link.getAttribute('data-page');
        if (page === 'calendar' && currentPath.includes('calendar.html')) {
            link.classList.add('active');
        } else if (page === 'reports' && (currentPath === '/' || currentPath.includes('index.html'))) {
            // index.html or root is the reports list (conceptually)
            link.classList.add('active');
        }
    });

    // Close menu on link click
    links.forEach(link => {
        link.addEventListener('click', () => {
            if (drawer.classList.contains('open')) {
                toggleMenu();
            }
        });
    });
});

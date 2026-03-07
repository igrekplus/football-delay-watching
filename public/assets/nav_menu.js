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

    const setMenuOpen = (isOpen) => {
        if (isOpen) {
            drawer.classList.add('open');
            overlay.classList.add('visible');
            btn.innerHTML = '✕';
            btn.setAttribute('aria-expanded', 'true');
            document.body.style.overflow = 'hidden'; // Prevent scroll
        } else {
            drawer.classList.remove('open');
            overlay.classList.remove('visible');
            btn.innerHTML = '☰';
            btn.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = ''; // Restore scroll
        }
    };

    const toggleMenu = () => {
        setMenuOpen(!drawer.classList.contains('open'));
    };

    const isTypingTarget = (target) => {
        if (!(target instanceof HTMLElement)) {
            return false;
        }

        const tagName = target.tagName;
        return (
            target.isContentEditable ||
            tagName === 'INPUT' ||
            tagName === 'TEXTAREA' ||
            tagName === 'SELECT'
        );
    };

    btn.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', toggleMenu);

    document.addEventListener('keydown', (event) => {
        if (
            event.defaultPrevented ||
            event.repeat ||
            event.ctrlKey ||
            event.metaKey ||
            event.altKey ||
            isTypingTarget(event.target)
        ) {
            return;
        }

        if (event.key === '[') {
            event.preventDefault();
            toggleMenu();
        }
    });

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
                setMenuOpen(false);
            }
        });
    });

    setMenuOpen(false);
});

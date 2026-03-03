// ==================== SIDEBAR HAMBURGER MENU FUNCTIONALITY ====================

document.addEventListener('DOMContentLoaded', function() {
    // Create hamburger button
    const hamburgerBtn = document.createElement('button');
    hamburgerBtn.className = 'hamburger-btn';
    hamburgerBtn.setAttribute('aria-label', 'Toggle menu');
    hamburgerBtn.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    
    // Add elements to body
    document.body.appendChild(hamburgerBtn);
    document.body.appendChild(overlay);
    
    // Get sidebar and main content
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // Toggle sidebar function
    function toggleSidebar() {
        hamburgerBtn.classList.toggle('active');
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
        
        // Prevent body scroll when sidebar is open on mobile
        if (sidebar.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
    
    // Close sidebar function
    function closeSidebar() {
        hamburgerBtn.classList.remove('active');
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // Event listeners
    hamburgerBtn.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);
    
    // Close sidebar when clicking on menu items (mobile only)
    const menuItems = sidebar.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            // Only close on mobile
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });
    
    // Close sidebar on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('active')) {
            closeSidebar();
        }
    });
    
    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            // Close sidebar if resizing to desktop
            if (window.innerWidth > 768 && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        }, 250);
    });
    
    // Prevent transitions on page load
    window.addEventListener('load', function() {
        sidebar.style.transition = 'transform var(--transition-normal), width var(--transition-normal)';
    });
});

// ==================== SMOOTH SCROLL TO TOP ON NAVIGATION ====================
document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});
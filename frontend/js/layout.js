/**
 * Layout.js - Client-side UI Component Architecture
 * Handles Sidebar injection, Header rendering, and Page Transitions.
 */

const Layout = {
    config: {
        active: '',
        title: '',
        subtitle: '',
        actions: null
    },

    init(config) {
        this.config = { ...this.config, ...config };

        // 1. Inject Styles for Transitions (if not in main.css)
        this.injectStyles();

        // 2. Render Components
        this.renderSidebar();

        // 3. Render Header
        const headerContainer = document.getElementById('header-container');
        if (headerContainer) {
            this.renderHeader(headerContainer);
        }

        // 4. Trigger Animation
        const main = document.querySelector('.main-content');
        if (main) {
            main.classList.add('animate-enter');
        }
    },

    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .main-content { opacity: 0; }
            .animate-enter { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        `;
        document.head.appendChild(style);
    },

    renderSidebar() {
        const sidebarContainer = document.getElementById('sidebar-container');
        if (!sidebarContainer) return;

        const menuItems = [
            { id: 'dashboard', label: 'Dashboard', href: 'admin.html', icon: '📊' },
            { id: 'employees', label: 'Employees', href: 'employees.html', icon: '👥' },
            { id: 'reports', label: 'Reports', href: 'reports.html', icon: '📈' },
            { id: 'register', label: 'Register New', href: 'register.html', icon: '✨' },
        ];

        const generateNav = () => menuItems.map(item => {
            const isActive = this.config.active === item.id ? 'active' : '';
            return `
                <a href="${item.href}" class="nav-item ${isActive}">
                    <span>${item.label}</span>
                </a>
            `;
        }).join('');

        sidebarContainer.innerHTML = `
            <aside class="sidebar">
                <a href="admin.html" class="brand">
                    <img src="/img/logo.png?v=3" alt="Sentinel" style="width: 140px; height: auto;">
                </a>
                <nav class="nav-menu">
                    ${generateNav()}
                    <a href="#" class="nav-item logout" id="logoutBtnLayout">
                        <span>Log Out</span>
                    </a>
                </nav>
            </aside>
        `;

        // Bind Logout
        setTimeout(() => {
            const btn = document.getElementById('logoutBtnLayout');
            if (btn && window.AUTH) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.AUTH.logout();
                });
            }
        }, 0);
    },

    renderHeader(container) {
        container.innerHTML = `
            <header class="header">
                <div>
                    <h1>${this.config.title}</h1>
                    <p>${this.config.subtitle}</p>
                </div>
                <div>
                    ${this.config.actions || ''}
                </div>
            </header>
        `;
    }
};

window.Layout = Layout;

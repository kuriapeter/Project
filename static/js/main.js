// Core Application JavaScript
class AppManager {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.setupEventListeners();
        this.initializeNotifications();
        this.setupThemeToggle();
    }

    setupEventListeners() {
        // Close flash messages
        document.querySelectorAll('.close-btn').forEach(button => {
            button.addEventListener('click', () => {
                button.closest('.alert').remove();
            });
        });

        // Auto-hide flash messages after 5 seconds
        setTimeout(() => {
            document.querySelectorAll('.flash-messages .alert').forEach(alert => {
                alert.remove();
            });
        }, 5000);

        // Toggle dropdowns
        document.querySelectorAll('.notifications-btn, .user-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const dropdown = btn.nextElementSibling;
                dropdown.classList.toggle('show');
            });
        });

        // Close dropdowns when clicking outside
        window.addEventListener('click', (e) => {
            if (!e.target.matches('.notifications-btn, .user-btn')) {
                document.querySelectorAll('.dropdown-content, .notifications-content').forEach(dropdown => {
                    if (dropdown.classList.contains('show')) {
                        dropdown.classList.remove('show');
                    }
                });
            }
        });
    }

    async initializeNotifications() {
        await this.updateNotifications();
        // Poll for new notifications every 30 seconds
        setInterval(() => this.updateNotifications(), 30000);
    }

    async updateNotifications() {
        try {
            const response = await this.fetchWithAuth('/api/notifications');
            const data = await response.json();

            // Update notification count
            const countElement = document.getElementById('notificationCount');
            if (countElement) {
                countElement.textContent = data.unread;
                countElement.style.display = data.unread > 0 ? 'block' : 'none';
            }

            // Update notification dropdown content
            const dropdownContent = document.getElementById('notificationsDropdown');
            if (dropdownContent && data.alerts) {
                dropdownContent.innerHTML = data.alerts.length > 0 
                    ? this.renderNotifications(data.alerts)
                    : '<div class="notification-item">No new notifications</div>';
            }
        } catch (error) {
            console.error('Error updating notifications:', error);
        }
    }

    renderNotifications(alerts) {
        return alerts.map(alert => `
            <div class="notification-item ${alert.type}">
                <div class="notification-header">
                    <i class="fas ${this.getAlertIcon(alert.type)}"></i>
                    <span class="notification-title">${alert.message}</span>
                </div>
                <div class="notification-body">${alert.details}</div>
            </div>
        `).join('');
    }

    getAlertIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            danger: 'fa-times-circle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', async () => {
                const currentTheme = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
                await this.setTheme(currentTheme);
            });
        }
    }

    async setTheme(theme) {
        try {
            const response = await this.fetchWithAuth('/api/preferences/theme', {
                method: 'POST',
                body: JSON.stringify({ theme })
            });

            if (response.ok) {
                document.body.className = `theme-${theme}`;
                localStorage.setItem('theme', theme);
            }
        } catch (error) {
            console.error('Error setting theme:', error);
        }
    }

    async fetchWithAuth(url, options = {}) {
        // Ensure headers object exists
        if (!options.headers) {
            options.headers = {};
        }

        // Add CSRF token and content type
        if (this.csrfToken) {
            options.headers['X-CSRFToken'] = this.csrfToken;
        }

        // Add JSON content type for non-GET requests
        if (options.method && options.method !== 'GET') {
            options.headers['Content-Type'] = 'application/json';
        }

        // Add credentials for session handling
        options.credentials = 'same-origin';

        try {
            const response = await fetch(url, options);

            // Handle session expiration
            if (response.status === 401) {
                window.location.href = '/auth/login';
                throw new Error('Session expired');
            }

            // Handle CSRF token errors
            if (response.status === 403) {
                // Refresh CSRF token
                const tokenResponse = await fetch('/api/refresh-csrf');
                if (tokenResponse.ok) {
                    const data = await tokenResponse.json();
                    this.csrfToken = data.csrf_token;
                    // Retry the original request
                    return this.fetchWithAuth(url, options);
                }
                throw new Error('CSRF token refresh failed');
            }

            return response;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }

    showAlert(type, message, duration = 5000) {
        const alertsContainer = document.querySelector('.flash-messages');
        if (!alertsContainer) return;

        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="close-btn">&times;</button>
        `;

        alertsContainer.appendChild(alert);

        // Add click handler for close button
        alert.querySelector('.close-btn').addEventListener('click', () => {
            alert.remove();
        });

        // Auto-remove after duration
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, duration);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(new Date(date));
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AppManager();
});

class AdminManager {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.initializeCharts();
        this.loadDashboardData();
        this.loadUsers();
        this.loadLogs();
        this.startHealthMonitoring();
    }

    initializeElements() {
        // User management
        this.userModal = document.getElementById('userModal');
        this.userForm = document.getElementById('userForm');
        this.userTableBody = document.getElementById('userTableBody');
        
        // System logs
        this.logLevel = document.getElementById('logLevel');
        this.logSearch = document.getElementById('logSearch');
        this.logContainer = document.getElementById('logContainer');
        
        // System update
        this.updateModal = document.getElementById('updateModal');
        this.updateChangelog = document.getElementById('updateChangelog');
        
        // Password visibility toggle
        this.passwordInput = document.getElementById('password');
        this.togglePasswordBtn = document.querySelector('.toggle-password');
    }

    setupEventListeners() {
        // Log filters
        this.logLevel.addEventListener('change', () => this.filterLogs());
        this.logSearch.addEventListener('input', () => this.filterLogs());
        
        // Password visibility toggle
        this.togglePasswordBtn.addEventListener('click', () => {
            const type = this.passwordInput.type === 'password' ? 'text' : 'password';
            this.passwordInput.type = type;
            this.togglePasswordBtn.querySelector('i').className = `fas fa-eye${type === 'password' ? '' : '-slash'}`;
        });
    }

    initializeCharts() {
        // CPU Usage Chart
        this.cpuChart = new Chart(document.getElementById('cpuChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        // Memory Usage Chart
        this.memoryChart = new Chart(document.getElementById('memoryChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        // Database Size Chart
        this.dbSizeChart = new Chart(document.getElementById('dbSizeChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'DB Size (MB)',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

        // Response Time Chart
        this.responseTimeChart = new Chart(document.getElementById('responseTimeChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [],
                    borderColor: 'rgb(255, 159, 64)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    async loadDashboardData() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/dashboard');
            const data = await response.json();
            
            // Update summary cards
            document.getElementById('totalUsers').textContent = data.total_users;
            document.getElementById('activeUsers').textContent = data.active_users;
            document.getElementById('totalTransactions').textContent = data.total_transactions;
            
            // Update trends
            const cards = document.querySelectorAll('.summary-cards .card');
            data.trends.forEach((trend, index) => {
                const trendValue = cards[index].querySelector('.trend-value');
                if (trendValue) {
                    trendValue.textContent = `${trend >= 0 ? '+' : ''}${trend}%`;
                    trendValue.className = `trend-value ${trend >= 0 ? 'positive' : 'negative'}`;
                }
            });
            
            // Update system health
            const healthStatus = document.querySelector('.health-status');
            healthStatus.innerHTML = `
                <span class="status-indicator ${data.system_health.status}"></span>
                <span class="status-text">${data.system_health.message}</span>
            `;
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            window.app.showAlert('error', 'Failed to load dashboard data');
        }
    }

    async loadUsers() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/users');
            const users = await response.json();
            
            this.userTableBody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.name}</td>
                    <td>${user.email}</td>
                    <td>
                        <span class="badge badge-${user.role}">${user.role}</span>
                    </td>
                    <td>
                        <span class="badge badge-${user.status}">${user.status}</span>
                    </td>
                    <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                    <td>
                        <div class="actions">
                            <button class="btn btn-icon" onclick="adminManager.editUser(${user.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-icon" onclick="adminManager.toggleUserStatus(${user.id})">
                                <i class="fas fa-${user.status === 'active' ? 'ban' : 'check'}"></i>
                            </button>
                            <button class="btn btn-icon" onclick="adminManager.deleteUser(${user.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading users:', error);
            window.app.showAlert('error', 'Failed to load users');
        }
    }

    async loadLogs() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/logs');
            const logs = await response.json();
            
            this.logs = logs; // Store logs for filtering
            this.renderLogs(logs);
        } catch (error) {
            console.error('Error loading logs:', error);
            window.app.showAlert('error', 'Failed to load system logs');
        }
    }

    renderLogs(logs) {
        this.logContainer.innerHTML = logs.map(log => `
            <div class="log-entry ${log.level.toLowerCase()}">
                <div class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</div>
                <div class="log-level">${log.level}</div>
                <div class="log-message">${log.message}</div>
                ${log.details ? `<div class="log-details">${log.details}</div>` : ''}
            </div>
        `).join('');
    }

    filterLogs() {
        const level = this.logLevel.value.toLowerCase();
        const search = this.logSearch.value.toLowerCase();
        
        const filteredLogs = this.logs.filter(log => {
            const matchesLevel = !level || log.level.toLowerCase() === level;
            const matchesSearch = !search || 
                log.message.toLowerCase().includes(search) ||
                (log.details && log.details.toLowerCase().includes(search));
            return matchesLevel && matchesSearch;
        });
        
        this.renderLogs(filteredLogs);
    }

    startHealthMonitoring() {
        // Update health metrics every 5 seconds
        setInterval(async () => {
            try {
                const response = await window.app.fetchWithAuth('/api/admin/health');
                const data = await response.json();
                
                // Update charts
                this.updateChart(this.cpuChart, data.cpu);
                this.updateChart(this.memoryChart, data.memory);
                this.updateChart(this.dbSizeChart, data.db_size);
                this.updateChart(this.responseTimeChart, data.response_time);
                
                // Update values
                document.getElementById('cpuValue').textContent = `${data.cpu.current}%`;
                document.getElementById('memoryValue').textContent = `${data.memory.current}%`;
                document.getElementById('dbSizeValue').textContent = `${data.db_size.current} MB`;
                document.getElementById('responseTimeValue').textContent = `${data.response_time.current} ms`;
            } catch (error) {
                console.error('Error updating health metrics:', error);
            }
        }, 5000);
    }

    updateChart(chart, data) {
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }

    showAddUserModal() {
        this.userForm.reset();
        document.getElementById('userId').value = '';
        this.userModal.querySelector('.modal-header h2').textContent = 'Add User';
        this.userModal.querySelector('.modal-footer .btn-primary').textContent = 'Add User';
        this.userModal.style.display = 'block';
    }

    async editUser(id) {
        try {
            const response = await window.app.fetchWithAuth(`/api/admin/users/${id}`);
            const user = await response.json();
            
            document.getElementById('userId').value = user.id;
            document.getElementById('name').value = user.name;
            document.getElementById('email').value = user.email;
            document.getElementById('username').value = user.username;
            document.getElementById('role').value = user.role;
            document.getElementById('password').value = '';
            
            this.userModal.querySelector('.modal-header h2').textContent = 'Edit User';
            this.userModal.querySelector('.modal-footer .btn-primary').textContent = 'Save Changes';
            this.userModal.style.display = 'block';
        } catch (error) {
            console.error('Error loading user:', error);
            window.app.showAlert('error', 'Failed to load user details');
        }
    }

    async saveUser() {
        const formData = new FormData(this.userForm);
        const data = Object.fromEntries(formData.entries());
        const id = document.getElementById('userId').value;

        try {
            const response = await window.app.fetchWithAuth(
                id ? `/api/admin/users/${id}` : '/api/admin/users',
                {
                    method: id ? 'PUT' : 'POST',
                    body: JSON.stringify(data)
                }
            );

            if (response.ok) {
                window.app.showAlert('success', `User ${id ? 'updated' : 'added'} successfully`);
                this.closeUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error saving user:', error);
            window.app.showAlert('error', `Failed to ${id ? 'update' : 'add'} user`);
        }
    }

    async toggleUserStatus(id) {
        try {
            const response = await window.app.fetchWithAuth(`/api/admin/users/${id}/toggle`, {
                method: 'PUT'
            });

            if (response.ok) {
                window.app.showAlert('success', 'User status updated successfully');
                this.loadUsers();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error toggling user status:', error);
            window.app.showAlert('error', 'Failed to update user status');
        }
    }

    async deleteUser(id) {
        if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await window.app.fetchWithAuth(`/api/admin/users/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                window.app.showAlert('success', 'User deleted successfully');
                this.loadUsers();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            window.app.showAlert('error', 'Failed to delete user');
        }
    }

    async backupDatabase() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/backup', {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                document.getElementById('lastBackupTime').textContent = new Date().toLocaleString();
                window.app.showAlert('success', 'Database backup completed successfully');
                
                // Download backup file
                const a = document.createElement('a');
                a.href = data.backup_url;
                a.download = `backup_${new Date().toISOString()}.sql`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                throw new Error('Backup failed');
            }
        } catch (error) {
            console.error('Error backing up database:', error);
            window.app.showAlert('error', 'Failed to backup database');
        }
    }

    async clearCache() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/cache', {
                method: 'DELETE'
            });

            if (response.ok) {
                document.getElementById('cacheSize').textContent = '0 MB';
                window.app.showAlert('success', 'Cache cleared successfully');
            } else {
                throw new Error('Cache clear failed');
            }
        } catch (error) {
            console.error('Error clearing cache:', error);
            window.app.showAlert('error', 'Failed to clear cache');
        }
    }

    async checkUpdates() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/updates');
            const update = await response.json();
            
            if (update.available) {
                document.getElementById('updateVersion').textContent = update.version;
                this.updateChangelog.innerHTML = update.changelog.map(item => 
                    `<li>${item}</li>`
                ).join('');
                this.updateModal.style.display = 'block';
            } else {
                window.app.showAlert('info', 'Your system is up to date');
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
            window.app.showAlert('error', 'Failed to check for updates');
        }
    }

    async installUpdate() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/updates/install', {
                method: 'POST'
            });

            if (response.ok) {
                window.app.showAlert('success', 'Update installed successfully. Please refresh the page.');
                this.closeUpdateModal();
                setTimeout(() => window.location.reload(), 2000);
            } else {
                throw new Error('Update installation failed');
            }
        } catch (error) {
            console.error('Error installing update:', error);
            window.app.showAlert('error', 'Failed to install update');
        }
    }

    closeUserModal() {
        this.userModal.style.display = 'none';
    }

    closeUpdateModal() {
        this.updateModal.style.display = 'none';
    }

    async exportLogs() {
        try {
            const response = await window.app.fetchWithAuth('/api/admin/logs/export');
            if (!response.ok) throw new Error('Export failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `system_logs_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting logs:', error);
            window.app.showAlert('error', 'Failed to export logs');
        }
    }
}

// Initialize admin manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.adminManager = new AdminManager();
});

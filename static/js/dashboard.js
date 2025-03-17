// Dashboard Initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startPeriodicUpdates();
});

// Initialize Dashboard Components
function initializeDashboard() {
    // Initialize Charts
    initializeCharts();
    
    // Load Initial Data
    updateDashboardData();
    
    // Initialize Notifications
    initializeNotifications();
}

// Setup Event Listeners
function setupEventListeners() {
    // Mobile Menu Toggle
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleMobileMenu);
    }
    
    // Transaction Filter
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => filterTransactions(btn.dataset.filter));
    });
    
    // Search Functionality
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
}

// Chart Initialization
function initializeCharts() {
    // Income vs Expenses Chart
    const incomeExpensesCtx = document.getElementById('incomeExpensesChart');
    if (incomeExpensesCtx) {
        new Chart(incomeExpensesCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Income',
                        borderColor: '#22c55e',
                        data: []
                    },
                    {
                        label: 'Expenses',
                        borderColor: '#ef4444',
                        data: []
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        enabled: true
                    }
                }
            }
        });
    }
    
    // Budget Overview Chart
    const budgetCtx = document.getElementById('budgetChart');
    if (budgetCtx) {
        new Chart(budgetCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#4f46e5',
                        '#818cf8',
                        '#22c55e',
                        '#f59e0b',
                        '#ef4444'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
}

// Update Dashboard Data
async function updateDashboardData() {
    showLoading();
    try {
        const response = await fetch('/api/dashboard/data');
        const data = await response.json();
        
        updateKPIs(data.kpis);
        updateCharts(data.charts);
        updateTransactionsList(data.transactions);
        updateNotifications(data.notifications);
        
        hideLoading();
    } catch (error) {
        console.error('Error updating dashboard:', error);
        showError('Failed to update dashboard data');
        hideLoading();
    }
}

// Update KPIs with Animations
function updateKPIs(kpis) {
    const kpiElements = document.querySelectorAll('.kpi-value');
    kpiElements.forEach(element => {
        const targetValue = parseFloat(element.dataset.target);
        const currentValue = parseFloat(element.textContent.replace(/[^0-9.-]+/g, ''));
        
        animateValue(element, currentValue, targetValue, 1000);
    });
}

// Animate Number Changes
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const animate = () => {
        current += increment;
        const finished = increment > 0 ? current >= end : current <= end;
        
        if (finished) {
            element.textContent = formatCurrency(end);
        } else {
            element.textContent = formatCurrency(current);
            requestAnimationFrame(animate);
        }
    };
    
    requestAnimationFrame(animate);
}

// Format Currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

// Loading State Management
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// Error Handling
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger animate-fade-in';
    errorDiv.textContent = message;
    
    const container = document.querySelector('.main-content');
    container.insertBefore(errorDiv, container.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Debounce Function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Mobile Menu Toggle
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('show');
}

// Start Periodic Updates
function startPeriodicUpdates() {
    // Update dashboard data every 5 minutes
    setInterval(updateDashboardData, 5 * 60 * 1000);
    
    // Update notifications every minute
    setInterval(updateNotifications, 60 * 1000);
}

// Initialize Notifications
function initializeNotifications() {
    if ('Notification' in window) {
        Notification.requestPermission();
    }
}

// Update Notifications
async function updateNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();
        
        const badge = document.querySelector('.notification-count');
        if (badge) {
            badge.textContent = data.unread;
            badge.style.display = data.unread > 0 ? 'flex' : 'none';
        }
        
        // Show browser notification for new items
        if (data.new && Notification.permission === 'granted') {
            new Notification('New Notification', {
                body: data.new[0].message,
                icon: '/static/img/notification-icon.png'
            });
        }
    } catch (error) {
        console.error('Error updating notifications:', error);
    }
}

// Filter Transactions
function filterTransactions(filter) {
    const transactions = document.querySelectorAll('.transaction-row');
    transactions.forEach(row => {
        const type = row.dataset.type;
        row.style.display = filter === 'all' || type === filter ? 'table-row' : 'none';
    });
    
    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
}

// Handle Search
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const transactions = document.querySelectorAll('.transaction-row');
    
    transactions.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? 'table-row' : 'none';
    });
}

// Dashboard Management
class DashboardManager {
    constructor() {
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        this.timeRangeSelect = document.getElementById('timeRange');
        this.charts = {
            revenueExpenses: null,
            cashFlow: null
        };
        this.eventSource = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeDashboard();
        this.setupRealtimeUpdates();
    }

    setupEventListeners() {
        if (this.timeRangeSelect) {
            this.timeRangeSelect.addEventListener('change', () => this.updateDashboard());
        }

        // Clean up when leaving the page
        window.addEventListener('beforeunload', () => {
            if (this.eventSource) {
                this.eventSource.close();
            }
        });
    }

    async initializeDashboard() {
        const data = await this.fetchDashboardData();
        if (data) {
            this.updateDashboardDisplay(data);
        }
    }

    async updateDashboard() {
        const timeRange = this.timeRangeSelect?.value || 'month';
        const data = await this.fetchDashboardData(timeRange);
        if (data) {
            this.updateDashboardDisplay(data);
        }
    }

    async fetchDashboardData(timeRange = 'month') {
        try {
            const response = await fetch(`/auth/api/dashboard-data?timeRange=${timeRange}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            this.showAlert('error', 'Failed to fetch dashboard data. Please try again later.');
            return null;
        }
    }

    updateDashboardDisplay(data) {
        this.updateKPIs(data);
        this.updateCharts(data);
        this.updateBudgetOverview(data.budgets);
        this.updateRecentActivity(data.recent_activity);
    }

    updateKPIs(data) {
        // Update main KPIs
        this.updateElement('total-revenue', this.formatCurrency(data.total_income));
        this.updateElement('total-expenses', this.formatCurrency(data.total_expenses));
        this.updateElement('net-profit', this.formatCurrency(data.total_income - data.total_expenses));

        // Update change indicators
        if (data.changes) {
            this.updateChangeIndicator('revenue-change', data.changes.income);
            this.updateChangeIndicator('expenses-change', data.changes.expenses);
            this.updateChangeIndicator('profit-change', data.changes.profit);
        }
    }

    updateCharts(data) {
        // Destroy existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart instanceof Chart) {
                chart.destroy();
            }
        });

        // Create new charts
        this.charts.revenueExpenses = this.createRevenueExpensesChart(data);
        this.charts.cashFlow = this.createCashFlowChart(data);
    }

    createRevenueExpensesChart(data) {
        const ctx = document.getElementById('revenueExpensesChart')?.getContext('2d');
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.dates,
                datasets: [
                    {
                        label: 'Income',
                        data: data.income,
                        backgroundColor: 'rgba(75, 192, 192, 0.5)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Expenses',
                        data: data.expenses,
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => this.formatCurrency(value)
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${this.formatCurrency(context.raw)}`
                        }
                    }
                }
            }
        });
    }

    createCashFlowChart(data) {
        const ctx = document.getElementById('cashFlowChart')?.getContext('2d');
        if (!ctx) return null;

        // Calculate cumulative cash flow
        const cashFlow = data.dates.map((_, index) => {
            const totalIncome = data.income.slice(0, index + 1).reduce((sum, val) => sum + val, 0);
            const totalExpenses = data.expenses.slice(0, index + 1).reduce((sum, val) => sum + val, 0);
            return totalIncome - totalExpenses;
        });

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Cash Flow',
                    data: cashFlow,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        ticks: {
                            callback: value => this.formatCurrency(value)
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => `Cash Flow: ${this.formatCurrency(context.raw)}`
                        }
                    }
                }
            }
        });
    }

    updateBudgetOverview(budgets) {
        const container = document.getElementById('budget-overview');
        if (!container || !Array.isArray(budgets)) return;

        container.innerHTML = budgets.map(budget => `
            <div class="budget-card ${this.getBudgetStatusClass(budget)}">
                <h4>${budget.category}</h4>
                <div class="budget-progress">
                    <div class="progress-bar" style="width: ${(budget.spent_amount / budget.budget_amount * 100)}%"></div>
                </div>
                <div class="budget-details">
                    <span>Budget: ${this.formatCurrency(budget.budget_amount)}</span>
                    <span>Spent: ${this.formatCurrency(budget.spent_amount)}</span>
                    <span>Remaining: ${this.formatCurrency(budget.remaining)}</span>
                </div>
            </div>
        `).join('');
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('recent-activity');
        if (!container || !Array.isArray(activities)) return;

        container.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">${this.getActivityIcon(activity.type)}</div>
                <div class="activity-content">
                    <div class="activity-title">${activity.description}</div>
                    <div class="activity-details">
                        <span>${this.formatCurrency(activity.amount)}</span>
                        <span>${this.formatDate(activity.date)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    setupRealtimeUpdates() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource('/auth/api/dashboard-stream');
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateDashboardDisplay(data);
            } catch (error) {
                console.error('Error processing real-time update:', error);
            }
        };

        this.eventSource.onerror = () => {
            this.eventSource.close();
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.setupRealtimeUpdates(), 5000);
        };
    }

    // Helper Methods
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    updateChangeIndicator(elementId, change) {
        const element = document.getElementById(elementId);
        if (element) {
            const formattedChange = `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`;
            element.textContent = formattedChange;
            element.className = `change-indicator ${change >= 0 ? 'positive' : 'negative'}`;
        }
    }

    getBudgetStatusClass(budget) {
        const spentPercentage = (budget.spent_amount / budget.budget_amount) * 100;
        if (spentPercentage >= 100) return 'over-budget';
        if (spentPercentage >= 80) return 'warning';
        return 'normal';
    }

    getActivityIcon(type) {
        const icons = {
            income: '💰',
            expense: '💸',
            transfer: '↔️',
            budget: '📊',
            payroll: '👥'
        };
        return icons[type] || '📝';
    }

    showAlert(type, message) {
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type}`;
        alertContainer.innerHTML = `
            ${message}
            <button type="button" class="close" onclick="this.parentElement.remove();">&times;</button>
        `;
        document.querySelector('.main-content')?.prepend(alertContainer);

        setTimeout(() => {
            alertContainer.style.opacity = '0';
            setTimeout(() => alertContainer.remove(), 300);
        }, 5000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

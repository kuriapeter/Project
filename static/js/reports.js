class ReportManager {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.initializeDefaultReport();
    }

    initializeElements() {
        // Filter elements
        this.reportType = document.getElementById('reportType');
        this.dateRange = document.getElementById('dateRange');
        this.startDate = document.getElementById('startDate');
        this.endDate = document.getElementById('endDate');
        this.format = document.getElementById('format');
        this.generateReportBtn = document.getElementById('generateReportBtn');
        
        // Report sections
        this.reportSections = {
            income_expense: document.getElementById('incomeExpenseReport'),
            budget_analysis: document.getElementById('budgetAnalysisReport'),
            category_breakdown: document.getElementById('categoryBreakdownReport'),
            trend_analysis: document.getElementById('trendAnalysisReport')
        };
        
        // Modal elements
        this.generateReportModal = document.getElementById('generateReportModal');
        this.progressBar = this.generateReportModal.querySelector('.progress-bar');
        this.progressText = this.generateReportModal.querySelector('.progress-text');
        
        // Set default date range
        this.updateDateRange(this.dateRange.value);
    }

    setupEventListeners() {
        // Report type change
        this.reportType.addEventListener('change', () => this.switchReportView());
        
        // Date range change
        this.dateRange.addEventListener('change', () => this.updateDateRange());
        
        // Custom date inputs
        [this.startDate, this.endDate].forEach(input => {
            input.addEventListener('change', () => this.loadReportData());
        });
        
        // Generate report button
        this.generateReportBtn.addEventListener('click', () => this.generateReport());
    }

    async initializeDefaultReport() {
        await this.loadReportData();
        this.switchReportView();
    }

    switchReportView() {
        // Hide all report sections
        Object.values(this.reportSections).forEach(section => {
            section.style.display = 'none';
        });
        
        // Show selected report section
        const selectedSection = this.reportSections[this.reportType.value];
        if (selectedSection) {
            selectedSection.style.display = 'block';
        }
        
        // Reload report data
        this.loadReportData();
    }

    updateDateRange() {
        const customDateRange = document.querySelector('.custom-date-range');
        const showCustom = this.dateRange.value === 'custom';
        customDateRange.style.display = showCustom ? 'block' : 'none';

        if (!showCustom) {
            const today = new Date();
            let start = new Date();
            let end = new Date();

            switch (this.dateRange.value) {
                case 'this_month':
                    start = new Date(today.getFullYear(), today.getMonth(), 1);
                    end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                    break;
                case 'last_month':
                    start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    end = new Date(today.getFullYear(), today.getMonth(), 0);
                    break;
                case 'this_quarter':
                    const quarter = Math.floor(today.getMonth() / 3);
                    start = new Date(today.getFullYear(), quarter * 3, 1);
                    end = new Date(today.getFullYear(), (quarter + 1) * 3, 0);
                    break;
                case 'last_quarter':
                    const lastQuarter = Math.floor((today.getMonth() - 3) / 3);
                    start = new Date(today.getFullYear(), lastQuarter * 3, 1);
                    end = new Date(today.getFullYear(), (lastQuarter + 1) * 3, 0);
                    break;
                case 'this_year':
                    start = new Date(today.getFullYear(), 0, 1);
                    end = new Date(today.getFullYear(), 11, 31);
                    break;
                case 'last_year':
                    start = new Date(today.getFullYear() - 1, 0, 1);
                    end = new Date(today.getFullYear() - 1, 11, 31);
                    break;
            }

            this.startDate.value = start.toISOString().split('T')[0];
            this.endDate.value = end.toISOString().split('T')[0];
            this.loadReportData();
        }
    }

    async loadReportData() {
        const params = new URLSearchParams({
            start_date: this.startDate.value,
            end_date: this.endDate.value
        });

        try {
            const response = await window.app.fetchWithAuth(`/api/reports/${this.reportType.value}?${params}`);
            const data = await response.json();
            
            switch (this.reportType.value) {
                case 'income_expense':
                    this.updateIncomeExpenseReport(data);
                    break;
                case 'budget_analysis':
                    this.updateBudgetAnalysisReport(data);
                    break;
                case 'category_breakdown':
                    this.updateCategoryBreakdownReport(data);
                    break;
                case 'trend_analysis':
                    this.updateTrendAnalysisReport(data);
                    break;
            }
        } catch (error) {
            console.error('Error loading report data:', error);
            window.app.showAlert('error', 'Failed to load report data');
        }
    }

    updateIncomeExpenseReport(data) {
        // Update summary cards
        document.getElementById('totalIncome').textContent = window.app.formatCurrency(data.total_income);
        document.getElementById('totalExpenses').textContent = window.app.formatCurrency(data.total_expenses);
        document.getElementById('netIncome').textContent = window.app.formatCurrency(data.net_income);
        
        // Update chart
        window.chartManager.createIncomeExpenseChart({
            labels: data.labels,
            income: data.income_data,
            expenses: data.expense_data
        });
    }

    updateBudgetAnalysisReport(data) {
        // Update summary cards
        document.getElementById('totalBudget').textContent = window.app.formatCurrency(data.total_budget);
        document.getElementById('totalSpent').textContent = window.app.formatCurrency(data.total_spent);
        document.getElementById('budgetVariance').textContent = window.app.formatCurrency(data.variance);
        
        // Update chart
        window.chartManager.createBudgetChart({
            categories: data.categories,
            budgets: data.budget_amounts,
            spent: data.spent_amounts
        });
    }

    updateCategoryBreakdownReport(data) {
        // Update chart
        window.chartManager.createCategoryChart({
            categories: data.categories,
            amounts: data.amounts
        });
        
        // Update table
        const tbody = document.getElementById('categoryTableBody');
        tbody.innerHTML = data.categories.map((category, index) => {
            const amount = data.amounts[index];
            const percentage = data.percentages[index];
            const change = data.changes[index];
            
            return `
                <tr>
                    <td>${category}</td>
                    <td>${window.app.formatCurrency(amount)}</td>
                    <td>${percentage.toFixed(1)}%</td>
                    <td class="trend ${change > 0 ? 'up' : change < 0 ? 'down' : 'neutral'}">
                        <i class="fas fa-arrow-${change > 0 ? 'up' : change < 0 ? 'down' : 'right'}"></i>
                        ${Math.abs(change).toFixed(1)}%
                    </td>
                </tr>
            `;
        }).join('');
    }

    updateTrendAnalysisReport(data) {
        // Update metrics
        document.getElementById('avgMonthlyIncome').textContent = window.app.formatCurrency(data.avg_monthly_income);
        document.getElementById('avgMonthlyExpenses').textContent = window.app.formatCurrency(data.avg_monthly_expenses);
        document.getElementById('savingsRate').textContent = `${data.savings_rate.toFixed(1)}%`;
        
        // Update trend indicators
        const indicators = document.querySelectorAll('.trend-indicator');
        [
            data.income_trend,
            data.expense_trend,
            data.savings_trend
        ].forEach((trend, index) => {
            const indicator = indicators[index];
            const icon = indicator.querySelector('i');
            const value = indicator.querySelector('span');
            
            icon.className = `fas fa-arrow-${trend > 0 ? 'up' : trend < 0 ? 'down' : 'right'}`;
            value.textContent = trend === 0 ? 'No change' : `${Math.abs(trend).toFixed(1)}%`;
            indicator.className = `trend-indicator ${trend > 0 ? 'up' : trend < 0 ? 'down' : 'neutral'}`;
        });
        
        // Update chart
        window.chartManager.createTrendChart({
            labels: data.labels,
            netIncome: data.net_income_data,
            movingAverage: data.moving_average
        });
    }

    async generateReport() {
        this.generateReportModal.style.display = 'block';
        this.progressBar.style.width = '0%';
        this.progressText.textContent = 'Generating report...';

        const params = new URLSearchParams({
            type: this.reportType.value,
            start_date: this.startDate.value,
            end_date: this.endDate.value,
            format: this.format.value
        });

        try {
            // Start progress animation
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 5;
                if (progress <= 90) {
                    this.progressBar.style.width = `${progress}%`;
                }
            }, 200);

            const response = await window.app.fetchWithAuth(`/api/reports/generate?${params}`);
            
            clearInterval(progressInterval);
            
            if (!response.ok) throw new Error('Failed to generate report');
            
            // Complete progress bar
            this.progressBar.style.width = '100%';
            this.progressText.textContent = 'Report generated successfully!';

            // Download the report
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `financial_report_${new Date().toISOString().split('T')[0]}.${this.format.value}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Close modal after a short delay
            setTimeout(() => this.closeModal(), 1500);
        } catch (error) {
            console.error('Error generating report:', error);
            this.progressText.textContent = 'Failed to generate report';
            this.progressBar.style.backgroundColor = 'var(--danger-color)';
            window.app.showAlert('error', 'Failed to generate report');
        }
    }

    closeModal() {
        this.generateReportModal.style.display = 'none';
        this.progressBar.style.width = '0%';
        this.progressBar.style.backgroundColor = ''; // Reset color
        this.progressText.textContent = 'Generating report...';
    }
}

// Initialize report manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.reportManager = new ReportManager();
});

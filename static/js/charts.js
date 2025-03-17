// Charts and Data Visualization Manager
class ChartManager {
    constructor() {
        this.charts = {};
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    padding: 12,
                    cornerRadius: 4
                }
            }
        };
    }

    // Income vs Expenses Chart
    createIncomeExpenseChart(data) {
        const ctx = document.getElementById('incomeExpenseChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.incomeExpense) {
            this.charts.incomeExpense.destroy();
        }

        this.charts.incomeExpense = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Income',
                        data: data.income,
                        backgroundColor: 'rgba(46, 204, 113, 0.5)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Expenses',
                        data: data.expenses,
                        backgroundColor: 'rgba(231, 76, 60, 0.5)',
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => window.app.formatCurrency(value)
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = window.app.formatCurrency(context.raw);
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Budget Overview Chart
    createBudgetChart(data) {
        const ctx = document.getElementById('budgetChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.budget) {
            this.charts.budget.destroy();
        }

        // Calculate percentages for each category
        const datasets = data.categories.map((category, index) => {
            const spent = data.spent[index];
            const budget = data.budgets[index];
            const percentage = (spent / budget) * 100;
            
            return {
                category,
                spent,
                budget,
                percentage
            };
        });

        // Sort by percentage for better visualization
        datasets.sort((a, b) => b.percentage - a.percentage);

        this.charts.budget = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: datasets.map(d => d.category),
                datasets: [
                    {
                        label: 'Spent',
                        data: datasets.map(d => d.spent),
                        backgroundColor: datasets.map(d => {
                            if (d.percentage >= 100) return 'rgba(231, 76, 60, 0.5)';  // Over budget
                            if (d.percentage >= 80) return 'rgba(241, 196, 15, 0.5)';  // Warning
                            return 'rgba(46, 204, 113, 0.5)';  // Good
                        }),
                        borderColor: datasets.map(d => {
                            if (d.percentage >= 100) return 'rgba(231, 76, 60, 1)';
                            if (d.percentage >= 80) return 'rgba(241, 196, 15, 1)';
                            return 'rgba(46, 204, 113, 1)';
                        }),
                        borderWidth: 1
                    },
                    {
                        label: 'Budget',
                        data: datasets.map(d => d.budget),
                        backgroundColor: 'rgba(52, 152, 219, 0.2)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1,
                        borderDash: [5, 5]
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => window.app.formatCurrency(value)
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const dataset = datasets[context.dataIndex];
                                const label = context.dataset.label || '';
                                const value = window.app.formatCurrency(context.raw);
                                const percentage = dataset.percentage.toFixed(1);
                                return `${label}: ${value} (${percentage}% of budget)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Category Distribution Chart
    createCategoryChart(data) {
        const ctx = document.getElementById('categoryChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.category) {
            this.charts.category.destroy();
        }

        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.categories,
                datasets: [{
                    data: data.amounts,
                    backgroundColor: [
                        'rgba(46, 204, 113, 0.5)',
                        'rgba(52, 152, 219, 0.5)',
                        'rgba(155, 89, 182, 0.5)',
                        'rgba(241, 196, 15, 0.5)',
                        'rgba(230, 126, 34, 0.5)',
                        'rgba(231, 76, 60, 0.5)',
                        'rgba(149, 165, 166, 0.5)'
                    ],
                    borderColor: [
                        'rgba(46, 204, 113, 1)',
                        'rgba(52, 152, 219, 1)',
                        'rgba(155, 89, 182, 1)',
                        'rgba(241, 196, 15, 1)',
                        'rgba(230, 126, 34, 1)',
                        'rgba(231, 76, 60, 1)',
                        'rgba(149, 165, 166, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                ...this.defaultOptions,
                cutout: '60%',
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = window.app.formatCurrency(context.raw);
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Trend Analysis Chart
    createTrendChart(data) {
        const ctx = document.getElementById('trendChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.trend) {
            this.charts.trend.destroy();
        }

        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Net Income',
                        data: data.netIncome,
                        borderColor: 'rgba(46, 204, 113, 1)',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Moving Average',
                        data: data.movingAverage,
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    y: {
                        ticks: {
                            callback: (value) => window.app.formatCurrency(value)
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = window.app.formatCurrency(context.raw);
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chartManager = new ChartManager();
});

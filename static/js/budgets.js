class BudgetManager {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.loadCategories();
        this.updateBudgetChart();
        this.updateSummary();
    }

    initializeElements() {
        // Form elements
        this.budgetForm = document.getElementById('budgetForm');
        this.budgetModal = document.getElementById('budgetModal');
        this.deleteModal = document.getElementById('deleteModal');
        this.modalTitle = document.getElementById('modalTitle');
        
        // Summary elements
        this.totalBudget = document.getElementById('totalBudget');
        this.totalSpent = document.getElementById('totalSpent');
        this.totalRemaining = document.getElementById('totalRemaining');
        
        // Export button
        this.exportBtn = document.getElementById('exportBtn');
        
        // Set default date range for new budgets (current month)
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        this.defaultStartDate = firstDay.toISOString().split('T')[0];
        this.defaultEndDate = lastDay.toISOString().split('T')[0];
    }

    setupEventListeners() {
        // Export event
        this.exportBtn.addEventListener('click', () => this.exportBudgets());
        
        // Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
    }

    async loadCategories() {
        try {
            const response = await window.app.fetchWithAuth('/api/categories/expense');
            const categories = await response.json();
            
            const categorySelect = document.getElementById('category');
            categorySelect.innerHTML = categories.map(cat => 
                `<option value="${cat}">${cat}</option>`
            ).join('');
        } catch (error) {
            console.error('Error loading categories:', error);
            window.app.showAlert('error', 'Failed to load categories');
        }
    }

    async updateBudgetChart() {
        try {
            const response = await window.app.fetchWithAuth('/api/budgets/overview');
            const data = await response.json();
            
            window.chartManager.createBudgetChart({
                categories: data.categories,
                budgets: data.budget_amounts,
                spent: data.spent_amounts
            });
        } catch (error) {
            console.error('Error updating budget chart:', error);
        }
    }

    async updateSummary() {
        try {
            const response = await window.app.fetchWithAuth('/api/budgets/summary');
            const data = await response.json();
            
            this.totalBudget.textContent = window.app.formatCurrency(data.total_budget);
            this.totalSpent.textContent = window.app.formatCurrency(data.total_spent);
            this.totalRemaining.textContent = window.app.formatCurrency(data.total_remaining);
            
            // Update color based on remaining amount
            const remainingPercentage = (data.total_remaining / data.total_budget) * 100;
            this.totalRemaining.className = 'amount ' + 
                (remainingPercentage <= 0 ? 'danger' : 
                 remainingPercentage <= 20 ? 'warning' : 
                 'success');
        } catch (error) {
            console.error('Error updating summary:', error);
        }
    }

    showAddModal() {
        this.modalTitle.textContent = 'Add Budget';
        document.getElementById('budgetId').value = '';
        document.getElementById('startDate').value = this.defaultStartDate;
        document.getElementById('endDate').value = this.defaultEndDate;
        this.budgetModal.style.display = 'block';
    }

    async editBudget(id) {
        try {
            const response = await window.app.fetchWithAuth(`/api/budgets/${id}`);
            const budget = await response.json();
            
            this.modalTitle.textContent = 'Edit Budget';
            document.getElementById('budgetId').value = budget.id;
            document.getElementById('category').value = budget.category;
            document.getElementById('budgetAmount').value = budget.budget_amount;
            document.getElementById('startDate').value = budget.start_date.split('T')[0];
            document.getElementById('endDate').value = budget.end_date.split('T')[0];
            document.getElementById('notes').value = budget.notes || '';
            
            this.budgetModal.style.display = 'block';
        } catch (error) {
            console.error('Error loading budget:', error);
            window.app.showAlert('error', 'Failed to load budget details');
        }
    }

    async saveBudget() {
        const formData = new FormData(this.budgetForm);
        const data = Object.fromEntries(formData.entries());
        const id = document.getElementById('budgetId').value;
        
        try {
            const response = await window.app.fetchWithAuth(
                id ? `/api/budgets/${id}` : '/api/budgets',
                {
                    method: id ? 'PUT' : 'POST',
                    body: JSON.stringify(data)
                }
            );
            
            if (response.ok) {
                window.app.showAlert('success', `Budget ${id ? 'updated' : 'added'} successfully`);
                this.closeModal();
                window.location.reload(); // Refresh to update all components
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error saving budget:', error);
            window.app.showAlert('error', `Failed to ${id ? 'update' : 'add'} budget`);
        }
    }

    deleteBudget(id) {
        this.deleteModal.style.display = 'block';
        this.deleteModal.dataset.budgetId = id;
    }

    async confirmDelete() {
        const id = this.deleteModal.dataset.budgetId;
        
        try {
            const response = await window.app.fetchWithAuth(`/api/budgets/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                window.app.showAlert('success', 'Budget deleted successfully');
                this.closeDeleteModal();
                window.location.reload(); // Refresh to update all components
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error deleting budget:', error);
            window.app.showAlert('error', 'Failed to delete budget');
        }
    }

    async exportBudgets() {
        try {
            const response = await window.app.fetchWithAuth('/api/budgets/export?format=csv');
            if (!response.ok) throw new Error('Export failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `budgets_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting budgets:', error);
            window.app.showAlert('error', 'Failed to export budgets');
        }
    }

    closeModal() {
        this.budgetModal.style.display = 'none';
        this.budgetForm.reset();
        document.getElementById('budgetId').value = '';
        this.modalTitle.textContent = 'Add Budget';
    }

    closeDeleteModal() {
        this.deleteModal.style.display = 'none';
        delete this.deleteModal.dataset.budgetId;
    }
}

// Initialize budget manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.budgetManager = new BudgetManager();
});

class TransactionManager {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.loadCategories();
        this.setupFilters();
    }

    initializeElements() {
        // Form elements
        this.transactionForm = document.getElementById('transactionForm');
        this.transactionModal = document.getElementById('transactionModal');
        this.deleteModal = document.getElementById('deleteModal');
        this.modalTitle = document.getElementById('modalTitle');
        
        // Filter elements
        this.typeFilter = document.getElementById('typeFilter');
        this.categoryFilter = document.getElementById('categoryFilter');
        this.startDate = document.getElementById('startDate');
        this.endDate = document.getElementById('endDate');
        this.applyFiltersBtn = document.getElementById('applyFilters');
        
        // Export button
        this.exportBtn = document.getElementById('exportBtn');
        
        // Set default date range (last 30 days)
        const today = new Date();
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(today.getDate() - 30);
        
        this.startDate.value = thirtyDaysAgo.toISOString().split('T')[0];
        this.endDate.value = today.toISOString().split('T')[0];
    }

    setupEventListeners() {
        // Filter events
        this.applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        
        // Export event
        this.exportBtn.addEventListener('click', () => this.exportTransactions());
        
        // Modal close buttons
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
        
        // Form type change event
        document.getElementById('type').addEventListener('change', (e) => {
            this.loadCategories(e.target.value);
        });
    }

    async loadCategories(type = null) {
        try {
            const response = await window.app.fetchWithAuth('/api/categories' + (type ? `?type=${type}` : ''));
            const categories = await response.json();
            
            // Update both filter and form category dropdowns
            [this.categoryFilter, document.getElementById('category')].forEach(select => {
                if (!select) return;
                
                const currentValue = select.value;
                select.innerHTML = '<option value="">All</option>' +
                    categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
                select.value = currentValue;
            });
        } catch (error) {
            console.error('Error loading categories:', error);
            window.app.showAlert('error', 'Failed to load categories');
        }
    }

    setupFilters() {
        // Initialize filter values from URL parameters
        const params = new URLSearchParams(window.location.search);
        this.typeFilter.value = params.get('type') || '';
        this.categoryFilter.value = params.get('category') || '';
        this.startDate.value = params.get('start_date') || this.startDate.value;
        this.endDate.value = params.get('end_date') || this.endDate.value;
    }

    async applyFilters() {
        const filters = {
            type: this.typeFilter.value,
            category: this.categoryFilter.value,
            start_date: this.startDate.value,
            end_date: this.endDate.value
        };

        // Update URL with filter parameters
        const params = new URLSearchParams(filters);
        window.history.pushState({}, '', `${window.location.pathname}?${params}`);

        try {
            const response = await window.app.fetchWithAuth(`/api/transactions?${params}`);
            const transactions = await response.json();
            this.updateTransactionTable(transactions);
        } catch (error) {
            console.error('Error applying filters:', error);
            window.app.showAlert('error', 'Failed to apply filters');
        }
    }

    updateTransactionTable(transactions) {
        const tbody = document.getElementById('transactionsTableBody');
        tbody.innerHTML = transactions.map(t => `
            <tr data-id="${t.id}" class="transaction-row ${t.type}">
                <td>${new Date(t.date).toLocaleDateString()}</td>
                <td>
                    <span class="badge ${t.type === 'income' ? 'badge-success' : 'badge-danger'}">
                        ${t.type.charAt(0).toUpperCase() + t.type.slice(1)}
                    </span>
                </td>
                <td>${t.category}</td>
                <td>${t.description}</td>
                <td class="amount ${t.type}">${window.app.formatCurrency(t.amount)}</td>
                <td>
                    <span class="badge badge-${t.status}">
                        ${t.status.charAt(0).toUpperCase() + t.status.slice(1)}
                    </span>
                </td>
                <td>
                    <div class="actions">
                        <button class="btn btn-icon" onclick="transactionManager.editTransaction(${t.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-icon" onclick="transactionManager.deleteTransaction(${t.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    async editTransaction(id) {
        try {
            const response = await window.app.fetchWithAuth(`/api/transactions/${id}`);
            const transaction = await response.json();
            
            this.modalTitle.textContent = 'Edit Transaction';
            document.getElementById('transactionId').value = transaction.id;
            document.getElementById('type').value = transaction.type;
            await this.loadCategories(transaction.type);
            document.getElementById('category').value = transaction.category;
            document.getElementById('amount').value = transaction.amount;
            document.getElementById('date').value = transaction.date.split('T')[0];
            document.getElementById('description').value = transaction.description;
            document.getElementById('status').value = transaction.status;
            
            this.transactionModal.style.display = 'block';
        } catch (error) {
            console.error('Error loading transaction:', error);
            window.app.showAlert('error', 'Failed to load transaction details');
        }
    }

    async saveTransaction() {
        const formData = new FormData(this.transactionForm);
        const data = Object.fromEntries(formData.entries());
        const id = document.getElementById('transactionId').value;
        
        try {
            const response = await window.app.fetchWithAuth(
                id ? `/api/transactions/${id}` : '/api/transactions',
                {
                    method: id ? 'PUT' : 'POST',
                    body: JSON.stringify(data)
                }
            );
            
            if (response.ok) {
                window.app.showAlert('success', `Transaction ${id ? 'updated' : 'added'} successfully`);
                this.closeModal();
                this.applyFilters();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error saving transaction:', error);
            window.app.showAlert('error', `Failed to ${id ? 'update' : 'add'} transaction`);
        }
    }

    deleteTransaction(id) {
        this.deleteModal.style.display = 'block';
        this.deleteModal.dataset.transactionId = id;
    }

    async confirmDelete() {
        const id = this.deleteModal.dataset.transactionId;
        
        try {
            const response = await window.app.fetchWithAuth(`/api/transactions/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                window.app.showAlert('success', 'Transaction deleted successfully');
                this.closeDeleteModal();
                this.applyFilters();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error deleting transaction:', error);
            window.app.showAlert('error', 'Failed to delete transaction');
        }
    }

    async exportTransactions() {
        const params = new URLSearchParams({
            type: this.typeFilter.value,
            category: this.categoryFilter.value,
            start_date: this.startDate.value,
            end_date: this.endDate.value,
            format: 'csv'
        });

        try {
            const response = await window.app.fetchWithAuth(`/api/transactions/export?${params}`);
            if (!response.ok) throw new Error('Export failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting transactions:', error);
            window.app.showAlert('error', 'Failed to export transactions');
        }
    }

    closeModal() {
        this.transactionModal.style.display = 'none';
        this.transactionForm.reset();
        document.getElementById('transactionId').value = '';
        this.modalTitle.textContent = 'Add Transaction';
    }

    closeDeleteModal() {
        this.deleteModal.style.display = 'none';
        delete this.deleteModal.dataset.transactionId;
    }
}

// Initialize transaction manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.transactionManager = new TransactionManager();
});

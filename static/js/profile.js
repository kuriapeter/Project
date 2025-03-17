class ProfileManager {
    constructor() {
        this.initializeElements();
        this.setupEventListeners();
        this.setupPasswordStrengthMeter();
        this.loadSecuritySettings();
    }

    initializeElements() {
        // Forms
        this.profileForm = document.getElementById('profileForm');
        this.passwordForm = document.getElementById('passwordForm');
        this.deleteAccountForm = document.getElementById('deleteAccountForm');
        
        // Password fields and toggles
        this.passwordInputs = document.querySelectorAll('.password-input input');
        this.toggleButtons = document.querySelectorAll('.toggle-password');
        
        // Security toggles
        this.twoFactorToggle = document.getElementById('twoFactorAuth');
        this.notificationsToggle = document.getElementById('loginNotifications');
        
        // Delete account modal
        this.deleteAccountModal = document.getElementById('deleteAccountModal');
        this.deleteConfirmation = document.getElementById('deleteConfirmation');
        this.deletePassword = document.getElementById('deletePassword');
    }

    setupEventListeners() {
        // Form submissions
        this.profileForm.addEventListener('submit', (e) => this.handleProfileUpdate(e));
        this.passwordForm.addEventListener('submit', (e) => this.handlePasswordChange(e));
        
        // Password visibility toggles
        this.toggleButtons.forEach((button, index) => {
            button.addEventListener('click', () => this.togglePasswordVisibility(this.passwordInputs[index], button));
        });
        
        // Security toggles
        this.twoFactorToggle.addEventListener('change', () => this.updateSecuritySetting('two_factor_auth'));
        this.notificationsToggle.addEventListener('change', () => this.updateSecuritySetting('login_notifications'));
        
        // Avatar upload preview
        const avatarInput = document.getElementById('avatar');
        if (avatarInput) {
            avatarInput.addEventListener('change', (e) => this.handleAvatarPreview(e));
        }
    }

    setupPasswordStrengthMeter() {
        const newPassword = document.getElementById('newPassword');
        const strengthBar = document.querySelector('.strength-indicator');
        const strengthText = document.querySelector('.strength-value');

        newPassword.addEventListener('input', () => {
            const strength = this.calculatePasswordStrength(newPassword.value);
            strengthBar.style.width = `${strength.score * 25}%`;
            strengthBar.className = `strength-indicator ${strength.class}`;
            strengthText.textContent = strength.label;
        });
    }

    calculatePasswordStrength(password) {
        let score = 0;
        const checks = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            numbers: /\d/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };

        score = Object.values(checks).filter(Boolean).length;

        const strengthLevels = [
            { score: 0, label: 'Very Weak', class: 'very-weak' },
            { score: 1, label: 'Weak', class: 'weak' },
            { score: 2, label: 'Medium', class: 'medium' },
            { score: 3, label: 'Strong', class: 'strong' },
            { score: 4, label: 'Very Strong', class: 'very-strong' }
        ];

        return strengthLevels[score] || strengthLevels[0];
    }

    async handleProfileUpdate(e) {
        e.preventDefault();
        const formData = new FormData(this.profileForm);

        try {
            const response = await window.app.fetchWithAuth('/api/profile', {
                method: 'PUT',
                body: formData
            });

            if (response.ok) {
                window.app.showAlert('success', 'Profile updated successfully');
                // Refresh page to show updated information
                window.location.reload();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            window.app.showAlert('error', 'Failed to update profile');
        }
    }

    async handlePasswordChange(e) {
        e.preventDefault();
        const formData = new FormData(this.passwordForm);
        const data = Object.fromEntries(formData.entries());

        // Validate password match
        if (data.new_password !== data.confirm_password) {
            window.app.showAlert('error', 'New passwords do not match');
            return;
        }

        try {
            const response = await window.app.fetchWithAuth('/api/profile/password', {
                method: 'PUT',
                body: JSON.stringify(data)
            });

            if (response.ok) {
                window.app.showAlert('success', 'Password changed successfully');
                this.passwordForm.reset();
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error changing password:', error);
            window.app.showAlert('error', 'Failed to change password');
        }
    }

    togglePasswordVisibility(input, button) {
        const type = input.type === 'password' ? 'text' : 'password';
        input.type = type;
        button.querySelector('i').className = `fas fa-eye${type === 'password' ? '' : '-slash'}`;
    }

    async loadSecuritySettings() {
        try {
            const response = await window.app.fetchWithAuth('/api/profile/security');
            const settings = await response.json();
            
            this.twoFactorToggle.checked = settings.two_factor_enabled;
            this.notificationsToggle.checked = settings.notifications_enabled;
        } catch (error) {
            console.error('Error loading security settings:', error);
        }
    }

    async updateSecuritySetting(setting) {
        const isEnabled = setting === 'two_factor_auth' ? 
            this.twoFactorToggle.checked : 
            this.notificationsToggle.checked;

        try {
            const response = await window.app.fetchWithAuth(`/api/profile/security/${setting}`, {
                method: 'PUT',
                body: JSON.stringify({ enabled: isEnabled })
            });

            if (response.ok) {
                window.app.showAlert('success', 'Security setting updated');
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error updating security setting:', error);
            window.app.showAlert('error', 'Failed to update security setting');
            
            // Revert toggle if update failed
            if (setting === 'two_factor_auth') {
                this.twoFactorToggle.checked = !isEnabled;
            } else {
                this.notificationsToggle.checked = !isEnabled;
            }
        }
    }

    handleAvatarPreview(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const avatar = document.querySelector('.profile-avatar img');
                if (avatar) {
                    avatar.src = e.target.result;
                } else {
                    const placeholder = document.querySelector('.avatar-placeholder');
                    if (placeholder) {
                        placeholder.innerHTML = `<img src="${e.target.result}" alt="Profile picture">`;
                    }
                }
            };
            reader.readAsDataURL(file);
        }
    }

    showDeleteAccountModal() {
        this.deleteAccountModal.style.display = 'block';
        this.deleteConfirmation.value = '';
        this.deletePassword.value = '';
    }

    closeDeleteModal() {
        this.deleteAccountModal.style.display = 'none';
    }

    async deleteAccount() {
        if (this.deleteConfirmation.value !== 'DELETE') {
            window.app.showAlert('error', 'Please type "DELETE" to confirm');
            return;
        }

        try {
            const response = await window.app.fetchWithAuth('/api/profile', {
                method: 'DELETE',
                body: JSON.stringify({
                    password: this.deletePassword.value
                })
            });

            if (response.ok) {
                window.app.showAlert('success', 'Account deleted successfully');
                window.location.href = '/logout';
            } else {
                const error = await response.json();
                throw new Error(error.message);
            }
        } catch (error) {
            console.error('Error deleting account:', error);
            window.app.showAlert('error', 'Failed to delete account');
        }
    }
}

// Initialize profile manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.profileManager = new ProfileManager();
});

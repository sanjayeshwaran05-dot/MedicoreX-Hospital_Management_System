
// Hospital Management System - Main JavaScript File

// Utility Functions
function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alertContainer.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// Format currency
function formatCurrency(amount) {
    return '\u20b9' + parseFloat(amount).toLocaleString();
}

// Format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

// Format datetime
function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString();
}

// Generate unique ID
function generateId(prefix) {
    return prefix + Date.now();
}

// Validate email
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Validate phone number
function validatePhone(phone) {
    const re = /^[6-9]\d{9}$/;
    return re.test(phone);
}

// Initialize data if not exists
function initializeData() {
    if (!localStorage.getItem('patients')) {
        localStorage.setItem('patients', JSON.stringify([]));
    }
    if (!localStorage.getItem('doctors')) {
        localStorage.setItem('doctors', JSON.stringify([]));
    }
    if (!localStorage.getItem('appointments')) {
        localStorage.setItem('appointments', JSON.stringify([]));
    }
    if (!localStorage.getItem('bills')) {
        localStorage.setItem('bills', JSON.stringify([]));
    }
}

// Check authentication
function checkAuth() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    return currentUser !== null;
}

// Logout
function logout() {
    localStorage.removeItem('currentUser');
    window.location.href = 'login.html';
}

// Get current user
function getCurrentUser() {
    return JSON.parse(localStorage.getItem('currentUser'));
}

// Save data to localStorage
function saveData(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
}

// Load data from localStorage
function loadData(key) {
    return JSON.parse(localStorage.getItem(key)) || [];
}

// Delete data from localStorage
function deleteData(key) {
    localStorage.removeItem(key);
}

// Confirm action
function confirmAction(message) {
    return confirm(message);
}

// Debounce function for search
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

// Export data to CSV
function exportToCSV(data, filename) {
    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => Object.values(row).join(','));
    const csvContent = [headers, ...rows].join('\
');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Print functionality
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<link rel="stylesheet" href="css/style.css">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeData();
    
    // Add common event listeners
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }

    // Check authentication for protected pages
    const protectedPages = ['dashboard.html', 'patients.html', 'doctors.html', 'appointments.html', 'billing.html', 'reports.html'];
    const currentPage = window.location.pathname.split('/').pop();
    
    if (protectedPages.includes(currentPage) && !checkAuth()) {
        window.location.href = 'login.html';
    }

    // Redirect to dashboard if already logged in
    if (currentPage === 'login.html' && checkAuth()) {
        window.location.href = 'dashboard.html';
    }
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('An error occurred:', e.error);
    if (checkAuth()) {
        showAlert('An error occurred. Please try again.', 'danger');
    }
});

// Prevent form resubmission on page refresh
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

console.log('Hospital Management System loaded successfully.');

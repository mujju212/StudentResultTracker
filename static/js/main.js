// Main JavaScript file for Student Results Portal
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initializeApp();
});

function initializeApp() {
    // Add fade-in animation to main containers
    addFadeInAnimations();
    
    // Initialize form enhancements
    initializeFormEnhancements();
    
    // Initialize result interactions
    initializeResultInteractions();
    
    // Initialize accessibility features
    initializeAccessibility();
    
    // Initialize loading states
    initializeLoadingStates();
}

function addFadeInAnimations() {
    // Add fade-in class to main containers
    const containers = document.querySelectorAll(
        '.welcome-container, .login-container, .student-info-card, .overall-results-card, .subjects-results-card'
    );
    
    containers.forEach((container, index) => {
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            container.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function initializeFormEnhancements() {
    // Enhanced form validation
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showFormErrors(this);
            } else {
                showLoadingState(this);
            }
        });
    });
    
    // Real-time input validation
    const inputs = document.querySelectorAll('.neumorphic-input');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateInput(this);
        });
        
        input.addEventListener('input', function() {
            clearInputError(this);
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredInputs = form.querySelectorAll('input[required]');
    
    requiredInputs.forEach(input => {
        if (!validateInput(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function validateInput(input) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required field validation
    if (input.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Name validation
    if (input.name === 'name' && value) {
        if (value.length < 2) {
            isValid = false;
            errorMessage = 'Name must be at least 2 characters long';
        } else if (!/^[a-zA-Z\s]+$/.test(value)) {
            isValid = false;
            errorMessage = 'Name can only contain letters and spaces';
        }
    }
    
    // Roll number validation
    if (input.name === 'roll_number' && value) {
        if (value.length < 1) {
            isValid = false;
            errorMessage = 'Roll number is required';
        }
    }
    
    // Show/hide error
    if (!isValid) {
        showInputError(input, errorMessage);
    } else {
        clearInputError(input);
    }
    
    return isValid;
}

function showInputError(input, message) {
    clearInputError(input);
    
    input.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback d-block';
    errorDiv.style.fontSize = '0.875rem';
    errorDiv.style.color = '#ef4444';
    errorDiv.style.marginTop = '0.25rem';
    errorDiv.textContent = message;
    
    input.parentNode.appendChild(errorDiv);
}

function clearInputError(input) {
    input.classList.remove('is-invalid');
    
    const existingError = input.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

function showFormErrors(form) {
    const firstInvalidInput = form.querySelector('.is-invalid');
    if (firstInvalidInput) {
        firstInvalidInput.focus();
        firstInvalidInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Please wait...';
        submitBtn.disabled = true;
        
        // Store original text for potential error recovery
        submitBtn.dataset.originalText = originalText;
    }
}

function initializeResultInteractions() {
    // Enhanced print functionality
    const printBtn = document.querySelector('.print-btn');
    if (printBtn) {
        printBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handlePrint();
        });
    }
    
    // Enhanced download functionality
    const downloadBtn = document.querySelector('.download-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function(e) {
            handleDownload(this);
        });
    }
    
    // Results table interactions
    initializeTableInteractions();
}

function handlePrint() {
    // Add print-specific styling
    const printStyles = `
        <style media="print">
            @page {
                margin: 1in;
                size: A4;
            }
            
            body {
                background: white !important;
                font-size: 12pt;
                line-height: 1.4;
            }
            
            .navbar, .action-buttons, .no-print {
                display: none !important;
            }
            
            .container {
                max-width: none !important;
                padding: 0 !important;
            }
            
            .student-info-card, .overall-results-card, .subjects-results-card {
                background: white !important;
                box-shadow: none !important;
                border: 1px solid #ddd !important;
                margin-bottom: 20px !important;
                page-break-inside: avoid;
            }
            
            .results-table {
                width: 100% !important;
                border-collapse: collapse !important;
            }
            
            .results-table th,
            .results-table td {
                border: 1px solid #ddd !important;
                padding: 8px !important;
                font-size: 11pt !important;
            }
            
            .results-table th {
                background: #f5f5f5 !important;
                color: #333 !important;
            }
            
            .student-name {
                font-size: 18pt !important;
                margin-bottom: 10px !important;
            }
            
            .metric-value {
                font-size: 14pt !important;
            }
        </style>
    `;
    
    // Add print styles to head
    const head = document.head || document.getElementsByTagName('head')[0];
    const printStyleSheet = document.createElement('style');
    printStyleSheet.setAttribute('media', 'print');
    printStyleSheet.innerHTML = printStyles;
    head.appendChild(printStyleSheet);
    
    // Trigger print
    window.print();
    
    // Remove print styles after printing
    setTimeout(() => {
        head.removeChild(printStyleSheet);
    }, 1000);
}

function handleDownload(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating PDF...';
    button.disabled = true;
    
    // Reset button after 3 seconds (PDF generation should complete by then)
    setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 3000);
}

function initializeTableInteractions() {
    const resultsTable = document.querySelector('.results-table');
    if (!resultsTable) return;
    
    // Add hover effects to table rows
    const tableRows = resultsTable.querySelectorAll('tbody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(102, 126, 234, 0.05)';
            this.style.transform = 'scale(1.005)';
            this.style.transition = 'all 0.2s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.background = '';
            this.style.transform = '';
        });
    });
    
    // Add click-to-highlight functionality
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            // Remove previous highlights
            tableRows.forEach(r => r.classList.remove('highlighted'));
            
            // Add highlight to clicked row
            this.classList.add('highlighted');
            
            // Remove highlight after 2 seconds
            setTimeout(() => {
                this.classList.remove('highlighted');
            }, 2000);
        });
    });
}

function initializeAccessibility() {
    // Keyboard navigation for section buttons
    const sectionBtns = document.querySelectorAll('.section-btn');
    
    sectionBtns.forEach(btn => {
        btn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // Focus management for forms
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const firstInput = form.querySelector('input');
        if (firstInput) {
            // Auto-focus first input after a short delay
            setTimeout(() => {
                firstInput.focus();
            }, 500);
        }
    });
    
    // Skip to content link
    addSkipToContentLink();
}

function addSkipToContentLink() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'visually-hidden-focusable';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 6px;
        background: var(--primary-color);
        color: white;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        z-index: 1000;
        transition: top 0.3s;
    `;
    
    skipLink.addEventListener('focus', function() {
        this.style.top = '6px';
    });
    
    skipLink.addEventListener('blur', function() {
        this.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Add main content id to appropriate container
    const mainContent = document.querySelector('.container, .welcome-container, .login-container');
    if (mainContent) {
        mainContent.id = 'main-content';
        mainContent.setAttribute('tabindex', '-1');
    }
}

function initializeLoadingStates() {
    // Show loading animation for sections
    const sectionsGrid = document.querySelector('.sections-grid');
    if (sectionsGrid && sectionsGrid.children.length === 0) {
        showLoadingPlaceholder(sectionsGrid);
    }
    
    // Handle page transitions
    const links = document.querySelectorAll('a:not([target="_blank"])');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't add loading for anchor links or javascript links
            if (this.getAttribute('href').startsWith('#') || 
                this.getAttribute('href').startsWith('javascript:')) {
                return;
            }
            
            showPageTransition();
        });
    });
}

function showLoadingPlaceholder(container) {
    container.innerHTML = `
        <div class="loading-placeholder">
            <div class="placeholder-item">
                <div class="placeholder-shimmer"></div>
                <div class="placeholder-text"></div>
            </div>
            <div class="placeholder-item">
                <div class="placeholder-shimmer"></div>
                <div class="placeholder-text"></div>
            </div>
            <div class="placeholder-item">
                <div class="placeholder-shimmer"></div>
                <div class="placeholder-text"></div>
            </div>
        </div>
    `;
}

function showPageTransition() {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(102, 126, 234, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    overlay.innerHTML = `
        <div style="text-align: center; color: white;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <div style="font-size: 1.1rem; font-weight: 500;">Loading...</div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Fade in overlay
    setTimeout(() => {
        overlay.style.opacity = '1';
    }, 10);
}

// Utility functions
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

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('Application error:', e.error);
    // Could send error to logging service in production
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    // Could send error to logging service in production
});

// Export functions for potential use in other scripts
window.StudentPortal = {
    validateForm,
    validateInput,
    showLoadingState,
    handlePrint,
    handleDownload
};

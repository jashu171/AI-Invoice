// File upload drag and drop functionality
document.addEventListener('DOMContentLoaded', function() {
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    
    // Prevent form from submitting normally
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const files = fileInput.files;
            if (files.length > 0) {
                uploadWithProgress(files[0]);
            }
        });
    }
    
    // Initialize file upload functionality
    setupFileUploadEvents();
    
    // Prevent default drag behaviors on document
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, function(e) {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
    
    // Smooth scroll for navigation
    const navLinks = document.querySelectorAll('.nav-item');
    navLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            // Add active class handling if needed
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Search functionality
    const searchInput = document.querySelector('.search-box input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const fileCards = document.querySelectorAll('.file-card');
            
            fileCards.forEach(function(card) {
                const fileName = card.querySelector('.file-name').textContent.toLowerCase();
                if (fileName.includes(searchTerm)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
    
    // File size formatting
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Update file sizes if needed
    const fileSizes = document.querySelectorAll('[data-file-size]');
    fileSizes.forEach(function(element) {
        const bytes = parseInt(element.dataset.fileSize);
        element.textContent = formatFileSize(bytes);
    });
});

// Invoice-specific functionality
function pushToAccounting(invoiceId) {
    if (!invoiceId) return;
    
    // Show loading state
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    button.disabled = true;
    
    fetch(`/api/invoices/${invoiceId}`)
        .then(response => response.json())
        .then(data => {
            const accountingPayload = {
                invoice_id: invoiceId,
                invoice_number: data.invoice_number,
                date: data.date,
                vendor: data.vendor,
                product_name: data.product_name,
                amount: data.total,
                tax: data.tax,
                address: data.address,
                processed_at: new Date().toISOString(),
                accounting_entries: {
                    debit: {
                        account: "Accounts Receivable",
                        amount: data.total
                    },
                    credit: {
                        account: "Sales Revenue", 
                        amount: data.total
                    }
                },
                raw_data: data
            };

            // Reset button state
            button.innerHTML = originalText;
            button.disabled = false;

            // Show JSON content modal
            showAccountingJSONModal(accountingPayload, invoiceId);
        })
        .catch(error => {
            showNotification('Error loading invoice data: ' + error.message, 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

function showAccountingJSONModal(payload, invoiceId) {
    const modal = document.createElement('div');
    modal.className = 'json-modal-overlay';
    modal.innerHTML = `
        <div class="json-modal">
            <div class="json-modal-header">
                <h3><i class="fas fa-file-code"></i> Accounting JSON Data</h3>
                <button class="close-modal" onclick="closeJSONModal()">&times;</button>
            </div>
            <div class="json-modal-body">
                <div class="json-actions">
                    <button class="btn btn-outline btn-sm" onclick="copyJSONToClipboard()">
                        <i class="fas fa-copy"></i> Copy JSON
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="downloadJSONFile('${invoiceId}')">
                        <i class="fas fa-download"></i> Download JSON
                    </button>
                </div>
                <pre class="json-content" id="jsonContent">${JSON.stringify(payload, null, 2)}</pre>
            </div>
            <div class="json-modal-footer">
                <button class="btn btn-outline" onclick="closeJSONModal()">Cancel</button>
                <button class="btn btn-primary" onclick="confirmPushToAccounting('${invoiceId}', this)">
                    <i class="fas fa-paper-plane"></i> Confirm Push to Accounting
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Add modal styles if not already present
    if (!document.getElementById('jsonModalStyles')) {
        const styles = document.createElement('style');
        styles.id = 'jsonModalStyles';
        styles.textContent = `
            .json-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .json-modal {
                background: white;
                border-radius: 8px;
                width: 90%;
                max-width: 800px;
                max-height: 90vh;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            .json-modal-header {
                padding: 20px;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .json-modal-header h3 {
                margin: 0;
                color: #1f2937;
            }
            .close-modal {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #6b7280;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .close-modal:hover {
                color: #374151;
            }
            .json-modal-body {
                padding: 20px;
                flex: 1;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            .json-actions {
                margin-bottom: 15px;
                display: flex;
                gap: 10px;
            }
            .json-content {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 15px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 12px;
                line-height: 1.5;
                overflow: auto;
                flex: 1;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .json-modal-footer {
                padding: 20px;
                border-top: 1px solid #e5e7eb;
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }
        `;
        document.head.appendChild(styles);
    }
}

function closeJSONModal() {
    const modal = document.querySelector('.json-modal-overlay');
    if (modal) {
        modal.remove();
    }
}

function copyJSONToClipboard() {
    const jsonContent = document.getElementById('jsonContent');
    if (jsonContent) {
        navigator.clipboard.writeText(jsonContent.textContent).then(() => {
            showNotification('JSON copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = jsonContent.textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('JSON copied to clipboard!', 'success');
        });
    }
}

function downloadJSONFile(invoiceId) {
    const jsonContent = document.getElementById('jsonContent');
    if (jsonContent) {
        const blob = new Blob([jsonContent.textContent], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `invoice_${invoiceId}_accounting.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showNotification('JSON file downloaded!', 'success');
    }
}

function confirmPushToAccounting(invoiceId, button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Pushing...';
    button.disabled = true;

    const jsonContent = document.getElementById('jsonContent');
    const payload = JSON.parse(jsonContent.textContent);

    fetch('/api/accounting/entries', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification(`Successfully pushed to accounting! Entry ID: ${result.entry_id}`, 'success');
            closeJSONModal();
            
            // Update the main push button
            const mainButton = document.querySelector(`button[onclick*="pushToAccounting('${invoiceId}')"]`);
            if (mainButton) {
                mainButton.innerHTML = '<i class="fas fa-check"></i> Pushed';
                mainButton.classList.remove('btn-outline', 'btn-primary');
                mainButton.classList.add('btn-success');
                mainButton.disabled = true;
            }
        } else {
            showNotification('Failed to push to accounting: ' + result.message, 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        showNotification('Error: ' + error.message, 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="close-flash" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add to page
    let flashContainer = document.querySelector('.flash-messages');
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.className = 'flash-messages';
        document.querySelector('.content').prepend(flashContainer);
    }
    
    flashContainer.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Initialize file upload functionality
function initializeFileUpload() {
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (!fileUploadArea || !fileInput) return;
    
    // Remove existing event listeners by cloning elements
    const newFileInput = fileInput.cloneNode(true);
    fileInput.parentNode.replaceChild(newFileInput, fileInput);
    
    const newUploadArea = fileUploadArea.cloneNode(true);
    fileUploadArea.parentNode.replaceChild(newUploadArea, fileUploadArea);
    
    // Re-add event listeners to new elements
    setupFileUploadEvents();
}

function setupFileUploadEvents() {
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (!fileUploadArea || !fileInput) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    fileUploadArea.addEventListener('drop', handleDrop, false);
    
    // Handle click to browse
    fileUploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Handle file selection
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files);
        }
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        fileUploadArea.classList.add('dragover');
    }
    
    function unhighlight(e) {
        fileUploadArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        fileInput.files = files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        // Use AJAX upload instead of form submission
        if (files.length > 0) {
            uploadWithProgress(files[0]);
        }
    }
}

function uploadWithProgress(file) {
    // Prevent multiple uploads of the same file
    if (window.uploadInProgress) {
        showNotification('Upload already in progress, please wait...', 'warning');
        return;
    }
    
    window.uploadInProgress = true;
    const formData = new FormData();
    formData.append('file', file);
    
    // Show progress
    showUploadProgress(file.name);
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (response.ok) {
            showNotification(`Invoice "${file.name}" processed successfully!`, 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            return response.text().then(text => {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            });
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showNotification(`Upload failed: ${error.message}`, 'error');
        hideUploadProgress();
    })
    .finally(() => {
        window.uploadInProgress = false;
    });
}

function showUploadProgress(filename) {
    const progressHtml = `
        <div id="uploadProgress" class="upload-progress">
            <div class="progress-info">
                <i class="fas fa-file-upload"></i>
                <span>Processing ${filename}...</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
        </div>
    `;
    
    const uploadArea = document.getElementById('fileUploadArea');
    uploadArea.innerHTML = progressHtml;
    
    // Animate progress bar
    setTimeout(() => {
        const progressFill = document.querySelector('.progress-fill');
        if (progressFill) {
            progressFill.style.width = '100%';
        }
    }, 100);
}

function hideUploadProgress() {
    const uploadArea = document.getElementById('fileUploadArea');
    if (uploadArea) {
        uploadArea.innerHTML = `
            <div class="upload-icon">
                <i class="fas fa-cloud-upload-alt"></i>
            </div>
            <div class="upload-text">
                <h3>Drag and drop files here</h3>
                <p>or <span class="browse-link">browse files</span></p>
                <small>Supports: PDF, PNG, JPG, JPEG, GIF (Max 16MB)</small>
            </div>
            <input type="file" name="file" id="fileInput" accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp" multiple>
        `;
        
        // Re-initialize drag and drop functionality
        initializeFileUpload();
    }
}

// Initialize enhanced features when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Add click handlers for invoice cards
    const invoiceCards = document.querySelectorAll('.invoice-card');
    invoiceCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't navigate if clicking on action buttons
            if (e.target.closest('.invoice-actions')) {
                return;
            }
            
            const invoiceId = this.dataset.invoiceId;
            if (invoiceId) {
                window.location.href = `/invoice/${invoiceId}`;
            }
        });
    });
    
    // Handle invoice row clicks in uploads table
    const invoiceRows = document.querySelectorAll('.invoice-row');
    invoiceRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't navigate if clicking on line items section
            if (e.target.closest('.line-items-section')) {
                return;
            }
            
            const invoiceId = this.dataset.invoiceId;
            if (invoiceId) {
                window.location.href = `/invoice/${invoiceId}`;
            }
        });
    });
    
    // Toggle line items visibility (optional enhancement)
    const lineItemsHeaders = document.querySelectorAll('.line-items-header');
    lineItemsHeaders.forEach(header => {
        const toggleBtn = document.createElement('button');
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
        toggleBtn.className = 'line-items-toggle';
        toggleBtn.style.cssText = 'background: none; border: none; color: #64748b; cursor: pointer; float: right; margin-top: -4px;';
        
        const h4 = header.querySelector('h4');
        if (h4) {
            h4.appendChild(toggleBtn);
            
            toggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const table = header.querySelector('.line-items-table');
                if (table) {
                    const isVisible = table.style.display !== 'none';
                    table.style.display = isVisible ? 'none' : 'table';
                    this.innerHTML = isVisible ? '<i class="fas fa-chevron-down"></i>' : '<i class="fas fa-chevron-up"></i>';
                }
            });
        }
    });
});
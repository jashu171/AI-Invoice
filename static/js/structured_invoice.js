/**
 * Structured Invoice JavaScript
 * Handles editing, validation, and interactions for structured invoice data
 */

// Global state
let editingSection = null;
let originalData = {};

document.addEventListener('DOMContentLoaded', function() {
    initializeStructuredInvoice();
});

function initializeStructuredInvoice() {
    // Add event listeners for edit buttons
    document.querySelectorAll('.edit-section-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.closest('.data-section').id;
            editSection(sectionId);
        });
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && editingSection) {
            cancelEdit();
        }
        if (e.ctrlKey && e.key === 's' && editingSection) {
            e.preventDefault();
            saveEdit();
        }
    });
}

function editSection(sectionId) {
    if (editingSection) {
        cancelEdit();
    }
    
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    editingSection = sectionId;
    originalData[sectionId] = captureOriginalData(section);
    
    // Convert section to editable
    convertToEditable(section);
    
    // Update UI
    section.classList.add('editing');
    updateEditButtons(section, true);
    
    showNotification(`Editing ${sectionId.replace('-', ' ')} section. Press Escape to cancel or Ctrl+S to save.`, 'info');
}

function captureOriginalData(section) {
    const data = {};
    section.querySelectorAll('.value').forEach((element, index) => {
        data[index] = element.textContent.trim();
    });
    return data;
}

function convertToEditable(section) {
    const sectionId = section.id;
    
    switch (sectionId) {
        case 'invoice-metadata':
            convertMetadataToEditable(section);
            break;
        case 'vendor-details':
        case 'customer-details':
            convertContactToEditable(section);
            break;
        case 'line-items':
            convertLineItemsToEditable(section);
            break;
        case 'summary':
            convertSummaryToEditable(section);
            break;
        case 'payment-terms':
            convertPaymentToEditable(section);
            break;
        case 'additional-info':
            convertAdditionalToEditable(section);
            break;
    }
}

function convertMetadataToEditable(section) {
    section.querySelectorAll('.data-item').forEach(item => {
        const label = item.querySelector('label').textContent;
        const valueElement = item.querySelector('.value');
        const currentValue = valueElement.textContent.trim();
        
        let inputHtml = '';
        
        if (label.toLowerCase().includes('date')) {
            inputHtml = `<input type="date" class="edit-input" value="${currentValue !== 'Not Found' ? currentValue : ''}" />`;
        } else if (label.toLowerCase().includes('currency')) {
            inputHtml = `
                <select class="edit-input">
                    <option value="USD" ${currentValue === 'USD' ? 'selected' : ''}>USD</option>
                    <option value="EUR" ${currentValue === 'EUR' ? 'selected' : ''}>EUR</option>
                    <option value="GBP" ${currentValue === 'GBP' ? 'selected' : ''}>GBP</option>
                    <option value="CAD" ${currentValue === 'CAD' ? 'selected' : ''}>CAD</option>
                </select>
            `;
        } else {
            inputHtml = `<input type="text" class="edit-input" value="${currentValue !== 'Not Found' ? currentValue : ''}" />`;
        }
        
        valueElement.innerHTML = inputHtml;
    });
}

function convertContactToEditable(section) {
    section.querySelectorAll('.data-item').forEach(item => {
        const label = item.querySelector('label').textContent;
        const valueElement = item.querySelector('.value');
        
        if (valueElement) {
            const currentValue = valueElement.textContent.trim();
            
            let inputType = 'text';
            if (label.toLowerCase().includes('email')) {
                inputType = 'email';
            } else if (label.toLowerCase().includes('phone')) {
                inputType = 'tel';
            } else if (label.toLowerCase().includes('website')) {
                inputType = 'url';
            }
            
            valueElement.innerHTML = `<input type="${inputType}" class="edit-input" value="${currentValue !== 'Not Found' ? currentValue : ''}" />`;
        }
        
        // Handle address blocks
        const addressBlock = item.querySelector('.address-block');
        if (addressBlock) {
            const lines = Array.from(addressBlock.children).map(div => div.textContent.trim());
            addressBlock.innerHTML = `
                <input type="text" class="edit-input" placeholder="Street Address" value="${lines[0] || ''}" />
                <input type="text" class="edit-input" placeholder="City, State ZIP" value="${lines[1] || ''}" />
                <input type="text" class="edit-input" placeholder="Country" value="${lines[2] || ''}" />
            `;
        }
    });
}

function convertLineItemsToEditable(section) {
    const table = section.querySelector('.line-items-table');
    if (!table) return;
    
    table.querySelectorAll('tbody tr').forEach(row => {
        // Make cells editable
        const cells = row.querySelectorAll('td');
        
        // Description
        const descCell = cells[0];
        if (descCell) {
            const value = descCell.textContent.trim();
            descCell.innerHTML = `<input type="text" class="edit-input" value="${value}" />`;
        }
        
        // Quantity
        const qtyCell = cells[1];
        if (qtyCell) {
            const value = qtyCell.textContent.trim();
            qtyCell.innerHTML = `<input type="number" class="edit-input" step="0.01" value="${value}" />`;
        }
        
        // Unit Price
        const priceCell = cells[2];
        if (priceCell) {
            const value = priceCell.textContent.replace('₹', '').trim();
            priceCell.innerHTML = `<input type="number" class="edit-input" step="0.01" value="${value !== '-' ? value : ''}" />`;
        }
        
        // Tax Rate
        const taxRateCell = cells[4];
        if (taxRateCell) {
            const value = taxRateCell.textContent.replace('%', '').trim();
            taxRateCell.innerHTML = `<input type="number" class="edit-input" step="0.1" min="0" max="100" value="${value}" />`;
        }
        
        // Category
        const categoryCell = cells[7];
        if (categoryCell) {
            const currentCategory = categoryCell.querySelector('.category-badge').textContent.toLowerCase();
            categoryCell.innerHTML = `
                <select class="edit-input">
                    <option value="product" ${currentCategory === 'product' ? 'selected' : ''}>Product</option>
                    <option value="service" ${currentCategory === 'service' ? 'selected' : ''}>Service</option>
                    <option value="tax" ${currentCategory === 'tax' ? 'selected' : ''}>Tax</option>
                    <option value="discount" ${currentCategory === 'discount' ? 'selected' : ''}>Discount</option>
                    <option value="other" ${currentCategory === 'other' ? 'selected' : ''}>Other</option>
                </select>
            `;
        }
    });
}

function convertSummaryToEditable(section) {
    section.querySelectorAll('.summary-item .value').forEach(valueElement => {
        const currentValue = valueElement.textContent.replace('₹', '').trim();
        valueElement.innerHTML = `<input type="number" class="edit-input" step="0.01" value="${currentValue}" />`;
    });
}

function convertPaymentToEditable(section) {
    section.querySelectorAll('.data-item').forEach(item => {
        const valueElement = item.querySelector('.value');
        if (valueElement) {
            const currentValue = valueElement.textContent.trim();
            valueElement.innerHTML = `<input type="text" class="edit-input" value="${currentValue !== 'Not specified' ? currentValue : ''}" />`;
        }
    });
}

function convertAdditionalToEditable(section) {
    section.querySelectorAll('.notes-content, .terms-content').forEach(element => {
        const currentValue = element.textContent.trim();
        element.innerHTML = `<textarea class="edit-input" rows="4">${currentValue}</textarea>`;
    });
}

function updateEditButtons(section, isEditing) {
    const editBtn = section.querySelector('.edit-section-btn');
    const actionsContainer = section.querySelector('.section-actions') || section.querySelector('.section-header');
    
    if (isEditing) {
        editBtn.style.display = 'none';
        
        // Add save/cancel buttons
        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-sm btn-success save-btn';
        saveBtn.innerHTML = '<i class="fas fa-check"></i> Save';
        saveBtn.onclick = () => saveEdit();
        
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-sm btn-outline cancel-btn';
        cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
        cancelBtn.onclick = () => cancelEdit();
        
        actionsContainer.appendChild(saveBtn);
        actionsContainer.appendChild(cancelBtn);
    } else {
        editBtn.style.display = 'inline-flex';
        
        // Remove save/cancel buttons
        const saveBtn = section.querySelector('.save-btn');
        const cancelBtn = section.querySelector('.cancel-btn');
        if (saveBtn) saveBtn.remove();
        if (cancelBtn) cancelBtn.remove();
    }
}

function saveEdit() {
    if (!editingSection) return;
    
    const section = document.getElementById(editingSection);
    const formData = collectFormData(section);
    
    // Validate data
    const validation = validateSectionData(editingSection, formData);
    if (!validation.isValid) {
        showNotification(`Validation errors: ${validation.errors.join(', ')}`, 'error');
        return;
    }
    
    // Send to server
    saveSectionData(editingSection, formData)
        .then(response => {
            if (response.success) {
                // Update display
                updateSectionDisplay(section, formData);
                exitEditMode(section);
                showNotification('Changes saved successfully!', 'success');
            } else {
                showNotification(`Save failed: ${response.message}`, 'error');
            }
        })
        .catch(error => {
            showNotification(`Save error: ${error.message}`, 'error');
        });
}

function cancelEdit() {
    if (!editingSection) return;
    
    const section = document.getElementById(editingSection);
    restoreOriginalData(section);
    exitEditMode(section);
    showNotification('Changes cancelled', 'info');
}

function exitEditMode(section) {
    section.classList.remove('editing');
    updateEditButtons(section, false);
    editingSection = null;
    delete originalData[section.id];
}

function collectFormData(section) {
    const data = {};
    const inputs = section.querySelectorAll('.edit-input');
    
    inputs.forEach((input, index) => {
        data[index] = input.value;
    });
    
    return data;
}

function validateSectionData(sectionId, data) {
    const errors = [];
    
    // Add validation logic based on section
    switch (sectionId) {
        case 'invoice-metadata':
            // Validate dates, required fields, etc.
            break;
        case 'line-items':
            // Validate quantities, prices, etc.
            break;
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

async function saveSectionData(sectionId, data) {
    const invoiceId = getInvoiceIdFromUrl();
    
    const response = await fetch(`/api/invoices/${invoiceId}/sections/${sectionId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    
    return await response.json();
}

function updateSectionDisplay(section, data) {
    // Convert inputs back to display format
    section.querySelectorAll('.edit-input').forEach((input, index) => {
        const value = data[index] || 'Not Found';
        const parent = input.parentElement;
        
        if (parent.classList.contains('value')) {
            parent.textContent = value;
        } else {
            // Handle complex structures like addresses
            parent.innerHTML = formatDisplayValue(value, parent);
        }
    });
}

function restoreOriginalData(section) {
    const sectionId = section.id;
    const original = originalData[sectionId];
    
    if (!original) return;
    
    section.querySelectorAll('.value').forEach((element, index) => {
        if (original[index] !== undefined) {
            element.textContent = original[index];
        }
    });
}

function formatDisplayValue(value, context) {
    // Format values based on context
    if (context.classList.contains('currency')) {
        return `₹${parseFloat(value || 0).toFixed(2)}`;
    }
    
    return value || 'Not Found';
}

function getInvoiceIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    return pathParts[pathParts.length - 1];
}

// Line Item Functions
function addLineItem() {
    showNotification('Add line item functionality would be implemented here', 'info');
}

function editLineItem(index) {
    showNotification(`Edit line item ${index + 1} functionality would be implemented here`, 'info');
}

function deleteLineItem(index) {
    if (confirm(`Are you sure you want to delete line item ${index + 1}?`)) {
        showNotification(`Delete line item ${index + 1} functionality would be implemented here`, 'info');
    }
}

// Action Functions
function pushToAccounting(invoiceId) {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    button.disabled = true;

    fetch(`/api/invoices/${invoiceId}`)
        .then(response => response.json())
        .then(data => {
            // Enhanced payload with structured data
            const accountingPayload = {
                invoice_data: data,
                structured_items: data.structured_data ? data.structured_data.line_items : data.line_items,
                accounting_format: {
                    totals: data.structured_data ? data.structured_data.summary : {
                        subtotal: 0,
                        tax_total: 0,
                        grand_total: data.total || 0
                    }
                }
            };

            return fetch('/api/accounting/entries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(accountingPayload)
            });
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showNotification(`Successfully pushed to accounting! Entry ID: ${result.entry_id}`, 'success');
                button.innerHTML = '<i class="fas fa-check"></i> Pushed';
                button.classList.remove('btn-primary');
                button.classList.add('btn-success');
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

function downloadJSON(invoiceId) {
    window.location.href = `/download/json/${invoiceId}`;
}

function reprocessWithAI(invoiceId) {
    if (confirm('Are you sure you want to reprocess this invoice with AI? This may overwrite existing data.')) {
        showNotification('AI reprocessing functionality would be implemented here', 'info');
    }
}

function deleteInvoice(invoiceId) {
    if (confirm('Are you sure you want to delete this invoice? This action cannot be undone.')) {
        showNotification('Delete functionality would be implemented here', 'info');
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="close-flash" onclick="this.parentElement.remove()">×</button>
    `;
    
    let flashContainer = document.querySelector('.flash-messages');
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.className = 'flash-messages';
        document.body.insertBefore(flashContainer, document.body.firstChild);
    }
    
    flashContainer.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Add CSS for edit inputs
const editStyles = `
<style>
.edit-input {
    width: 100%;
    padding: 6px 8px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 14px;
    font-family: inherit;
    background: white;
}

.edit-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.data-section.editing {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.save-btn {
    margin-left: 8px;
}

.cancel-btn {
    margin-left: 4px;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', editStyles);
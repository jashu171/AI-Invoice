{% extends "base.html" %}

{% block page_title %}File Uploads: UPL{{ "%.0f"|format(range(100000, 999999)|random) }}{% endblock %}

{% block content %}
<div class="invoice-layout">
    <!-- Main Invoice Area -->
    <div class="invoice-main">
        <div class="invoice-header">
            <div class="company-info">
                <div class="company-logo">
                    <div class="logo-icon">m</div>
                    <span class="company-name">Maglo</span>
                </div>
                <div class="company-details">
                    <p>sales@maglo.com</p>
                    <p>1333 Grey Fox Farm Road</p>
                    <p>Houston, TX 77060</p>
                    <p>Bloomfield Hills, Michigan MI, 48301</p>
                </div>
            </div>
        </div>

        <div class="invoice-details">
            <div class="invoice-info">
                <div class="info-row">
                    <span class="label">Upload Session</span>
                    <span class="value">UPL{{ "%.0f"|format(range(100000, 999999)|random) }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Session Date:</span>
                    <span class="value">{{ moment().format('DD MMM YYYY') if moment else '10 Apr 2022' }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Status:</span>
                    <span class="value">Active</span>
                </div>
            </div>

            <div class="billed-to">
                <h3>Upload Location</h3>
                <p>Local Server</p>
                <p>./uploads/</p>
                <p>Secure Storage</p>
            </div>
        </div>

        <div class="item-details">
            <h3>File Details</h3>
            <p class="subtitle">Files uploaded in this session</p>

            <table class="items-table">
                <thead>
                    <tr>
                        <th>INVOICE #</th>
                        <th>VENDOR</th>
                        <th>DATE</th>
                        <th>AMOUNT</th>
                    </tr>
                </thead>
                <tbody>
                    {% if invoices and invoices|length > 0 %}
                    {% for invoice in invoices %}
                    <tr data-invoice-id="{{ invoice.id }}" class="invoice-row" style="cursor: pointer;">
                        <td>{{ invoice.invoice_number or 'N/A' }}</td>
                        <td>{{ invoice.vendor or 'Unknown' }}</td>
                        <td>{{ invoice.date or 'N/A' }}</td>
                        <td>₹{{ invoice.total or '0.00' }}</td>
                    </tr>

                    {% endfor %}
                    {% else %}
                    <tr>
                        <td colspan="4" class="no-files">No invoices processed yet</td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>

            <div class="add-item">
                <form action="{{ url_for('upload_file') }}" method="post" enctype="multipart/form-data"
                    class="inline-upload">
                    <input type="file" name="file" id="quickUpload" accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp"
                        style="display: none;">
                    <button type="button" class="add-item-btn" onclick="document.getElementById('quickUpload').click()">
                        <i class="fas fa-plus"></i> Add File
                    </button>
                </form>
            </div>

            <div class="totals">
                <div class="total-row">
                    <span class="label">Total Invoices</span>
                    <span class="value">{{ invoices|length if invoices else 0 }}</span>
                </div>
                <div class="total-row">
                    <span class="label">Total Amount</span>
                    <span class="value">
                        {% set total_sum = 0 %}
                        {% if invoices %}
                        {% for invoice in invoices %}
                        {% if invoice.total and invoice.total != 'N/A' %}
                        {% set total_sum = total_sum + (invoice.total|float) %}
                        {% endif %}
                        {% endfor %}
                        {% endif %}
                        ₹{{ "%.2f"|format(total_sum) }}
                    </span>
                </div>
                <div class="total-row final">
                    <span class="label">Status</span>
                    <span class="value">{{ invoices|length if invoices else 0 }} Processed</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Sidebar -->
    <div class="invoice-sidebar">
        <div class="client-details">
            <h3>Session Details</h3>
            <div class="client-avatar">
                <img src="https://via.placeholder.com/48x48/4A5568/FFFFFF?text=FS" alt="File System">
            </div>
            <div class="client-info">
                <h4>File System</h4>
                <p>system@localhost.com</p>
            </div>
            <div class="client-company">
                <h4>Local Storage</h4>
                <p>./uploads/ directory</p>
            </div>

            <button class="btn btn-outline btn-sm">
                <i class="fas fa-folder-open"></i> Open Folder
            </button>
        </div>

        <div class="basic-info">
            <h3>Basic Info</h3>

            <div class="info-field">
                <label>Session Date</label>
                <div class="date-input">
                    <input type="date" value="{{ moment().format('YYYY-MM-DD') if moment else '2022-04-14' }}">
                    <i class="fas fa-calendar"></i>
                </div>
            </div>

            <div class="info-field">
                <label>Expiry Date</label>
                <div class="date-input">
                    <input type="date"
                        value="{{ moment().add(30, 'days').format('YYYY-MM-DD') if moment else '2022-04-20' }}">
                    <i class="fas fa-calendar"></i>
                </div>
            </div>

            <button class="btn btn-primary btn-full">
                <i class="fas fa-upload"></i> Upload More Files
            </button>

            <div class="action-buttons">
                <button class="btn btn-outline btn-sm">
                    <i class="fas fa-eye"></i> Preview
                </button>
                <button class="btn btn-outline btn-sm">
                    <i class="fas fa-download"></i> Download All
                </button>
            </div>
        </div>
    </div>
</div>

<script>
    document.getElementById('quickUpload').addEventListener('change', function () {
        if (this.files.length > 0) {
            this.closest('form').submit();
        }
    });

    // Handle invoice row clicks
    document.addEventListener('DOMContentLoaded', function () {
        const invoiceRows = document.querySelectorAll('.invoice-row');
        invoiceRows.forEach(function (row) {
            row.addEventListener('click', function () {
                const invoiceId = this.getAttribute('data-invoice-id');
                if (invoiceId) {
                    window.location.href = '/invoice/' + invoiceId;
                }
            });
        });
    });
</script>
{% endblock %}
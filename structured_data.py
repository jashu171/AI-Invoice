"""
Structured data models for invoice processing.
Defines the schema and validation for AI-extracted invoice data.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re


@dataclass
class Address:
    """Address information."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if address has minimum required information."""
        return bool(self.street and self.city)


@dataclass
class Contact:
    """Contact information."""
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    
    def validate_email(self) -> bool:
        """Validate email format."""
        if not self.email:
            return True
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, self.email))


@dataclass
class InvoiceMetadata:
    """Invoice metadata information."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    currency: Optional[str] = "USD"
    language: Optional[str] = "en"
    
    def validate_dates(self) -> List[str]:
        """Validate date formats."""
        errors = []
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        
        if self.invoice_date and not re.match(date_pattern, self.invoice_date):
            errors.append("Invoice date must be in YYYY-MM-DD format")
        
        if self.due_date and not re.match(date_pattern, self.due_date):
            errors.append("Due date must be in YYYY-MM-DD format")
        
        return errors


@dataclass
class VendorDetails:
    """Vendor/supplier information."""
    name: Optional[str] = None
    address: Address = field(default_factory=Address)
    contact: Contact = field(default_factory=Contact)
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None


@dataclass
class CustomerDetails:
    """Customer/buyer information."""
    name: Optional[str] = None
    address: Address = field(default_factory=Address)
    contact: Contact = field(default_factory=Contact)
    customer_id: Optional[str] = None


@dataclass
class LineItem:
    """Individual line item in the invoice."""
    item_id: Optional[str] = None
    description: Optional[str] = None
    quantity: float = 0.0
    unit_price: Optional[float] = None
    unit_type: Optional[str] = None
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    category: str = "other"  # product, service, tax, discount, other
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total amounts."""
        if self.unit_price is not None and self.quantity is not None:
            self.subtotal = self.quantity * self.unit_price
        
        if self.tax_rate is not None and self.tax_rate > 0 and self.subtotal is not None:
            self.tax_amount = self.subtotal * self.tax_rate
        
        if self.subtotal is not None and self.tax_amount is not None:
            self.total = self.subtotal + self.tax_amount
        elif self.subtotal is not None:
            self.total = self.subtotal
    
    def validate(self) -> List[str]:
        """Validate line item data."""
        errors = []
        
        if not self.description:
            errors.append("Line item description is required")
        
        if self.quantity is not None and self.quantity < 0:
            errors.append("Quantity cannot be negative")
        
        if self.unit_price is not None and self.unit_price < 0:
            errors.append("Unit price cannot be negative")
        
        if self.tax_rate is not None and (self.tax_rate < 0 or self.tax_rate > 1):
            errors.append("Tax rate must be between 0 and 1")
        
        return errors


@dataclass
class TaxBreakdown:
    """Tax breakdown information."""
    tax_type: str
    rate: float
    amount: float
    description: Optional[str] = None


@dataclass
class Summary:
    """Invoice summary and totals."""
    subtotal: float = 0.0
    tax_breakdown: List[TaxBreakdown] = field(default_factory=list)
    total_tax: float = 0.0
    discounts: float = 0.0
    shipping: float = 0.0
    grand_total: float = 0.0
    
    def calculate_totals(self, line_items: List[LineItem]):
        """Calculate summary totals from line items."""
        self.subtotal = sum(item.subtotal or 0 for item in line_items if item.category != 'tax')
        self.total_tax = sum(item.tax_amount or 0 for item in line_items)
        self.grand_total = (self.subtotal or 0) + (self.total_tax or 0) + (self.shipping or 0) - (self.discounts or 0)


@dataclass
class BankDetails:
    """Bank account information."""
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    routing_number: Optional[str] = None
    iban: Optional[str] = None
    swift_code: Optional[str] = None


@dataclass
class PaymentTerms:
    """Payment terms and methods."""
    terms: Optional[str] = None
    payment_methods: List[str] = field(default_factory=list)
    bank_details: BankDetails = field(default_factory=BankDetails)


@dataclass
class AdditionalInfo:
    """Additional invoice information."""
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    reference_numbers: List[str] = field(default_factory=list)


@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process."""
    method: str = "unknown"  # gemini_ai, regex_fallback, manual
    model: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    fallback_used: bool = False
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: List[str] = field(default_factory=list)


@dataclass
class StructuredInvoiceData:
    """Complete structured invoice data."""
    extraction_metadata: ExtractionMetadata = field(default_factory=ExtractionMetadata)
    invoice_metadata: InvoiceMetadata = field(default_factory=InvoiceMetadata)
    vendor_details: VendorDetails = field(default_factory=VendorDetails)
    customer_details: CustomerDetails = field(default_factory=CustomerDetails)
    line_items: List[LineItem] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    payment_terms: PaymentTerms = field(default_factory=PaymentTerms)
    additional_info: AdditionalInfo = field(default_factory=AdditionalInfo)
    
    def validate(self) -> List[str]:
        """Validate all structured data."""
        errors = []
        
        # Validate metadata
        errors.extend(self.invoice_metadata.validate_dates())
        
        # Validate contact information
        if not self.vendor_details.contact.validate_email():
            errors.append("Invalid vendor email format")
        
        if not self.customer_details.contact.validate_email():
            errors.append("Invalid customer email format")
        
        # Validate line items
        for i, item in enumerate(self.line_items):
            item_errors = item.validate()
            for error in item_errors:
                errors.append(f"Line item {i+1}: {error}")
        
        return errors
    
    def calculate_all_totals(self):
        """Calculate all totals and ensure consistency."""
        # Calculate line item totals
        for item in self.line_items:
            item.calculate_totals()
        
        # Calculate summary totals
        self.summary.calculate_totals(self.line_items)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuredInvoiceData':
        """Create instance from dictionary."""
        # Handle nested objects
        if 'extraction_metadata' in data:
            data['extraction_metadata'] = ExtractionMetadata(**data['extraction_metadata'])
        
        if 'invoice_metadata' in data:
            data['invoice_metadata'] = InvoiceMetadata(**data['invoice_metadata'])
        
        if 'vendor_details' in data:
            vendor_data = data['vendor_details']
            if 'address' in vendor_data:
                vendor_data['address'] = Address(**vendor_data['address'])
            if 'contact' in vendor_data:
                vendor_data['contact'] = Contact(**vendor_data['contact'])
            data['vendor_details'] = VendorDetails(**vendor_data)
        
        if 'customer_details' in data:
            customer_data = data['customer_details']
            if 'address' in customer_data:
                customer_data['address'] = Address(**customer_data['address'])
            if 'contact' in customer_data:
                customer_data['contact'] = Contact(**customer_data['contact'])
            data['customer_details'] = CustomerDetails(**customer_data)
        
        if 'line_items' in data:
            data['line_items'] = [LineItem(**item) for item in data['line_items']]
        
        if 'summary' in data:
            summary_data = data['summary']
            if 'tax_breakdown' in summary_data:
                summary_data['tax_breakdown'] = [
                    TaxBreakdown(**tax) for tax in summary_data['tax_breakdown']
                ]
            data['summary'] = Summary(**summary_data)
        
        if 'payment_terms' in data:
            payment_data = data['payment_terms']
            if 'bank_details' in payment_data:
                payment_data['bank_details'] = BankDetails(**payment_data['bank_details'])
            data['payment_terms'] = PaymentTerms(**payment_data)
        
        if 'additional_info' in data:
            data['additional_info'] = AdditionalInfo(**data['additional_info'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StructuredInvoiceData':
        """Create instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy format for backward compatibility."""
        return {
            "invoice_number": self.invoice_metadata.invoice_number,
            "date": self.invoice_metadata.invoice_date,
            "vendor": self.vendor_details.name,
            "total": str(self.summary.grand_total) if self.summary.grand_total else None,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "amount": item.total,
                    "item_type": item.category,
                    "formatted_amount": f"₹{item.total:.2f}",
                    "formatted_quantity": f"{item.quantity:.0f}" if item.quantity == int(item.quantity) else f"{item.quantity:.2f}"
                }
                for item in self.line_items
            ],
            "processed_at": self.extraction_metadata.extracted_at,
            "extraction_method": self.extraction_metadata.method,
            "structured_data": self.to_dict()
        }
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    jsonify,
)
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import json
import re
import pytesseract
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path
import cv2
import numpy as np
from dateutil import parser
import pandas as pd
import requests
import logging

# Import our new modules
from config import config
from gemini_extractor import GeminiAIExtractor
from structured_data import StructuredInvoiceData

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["PROCESSED_FOLDER"] = "processed"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"}

# Create directories if they don't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "pdf":
        return "PDF Document"
    elif ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
        return "Image File"
    return "Unknown"


class InvoiceProcessor:
    def __init__(self):
        # Initialize Gemini AI extractor
        self.gemini_extractor = GeminiAIExtractor()
        
        # Enhanced invoice patterns for better extraction
        self.patterns = {
            "invoice_number": [
                r"invoice\s*#?\s*:?\s*([A-Z0-9\-\/]+)",
                r"inv\s*#?\s*:?\s*([A-Z0-9\-\/]+)",
                r"bill\s*#?\s*:?\s*([A-Z0-9\-\/]+)",
                r"receipt\s*#?\s*:?\s*([A-Z0-9\-\/]+)",
                r"#\s*([A-Z0-9\-\/]+)",
                r"invoice\s*no\.?\s*:?\s*([A-Z0-9\-\/]+)",
            ],
            "date": [
                r"date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
                r"invoice\s*date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
                r"bill\s*date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
                r"(\d{4}-\d{2}-\d{2})",
                r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            ],
            "total": [
                r"total\s*:?\s*₹?\$?€?£?([0-9,]+\.?\d{0,2})",
                r"amount\s*due\s*:?\s*₹?\$?€?£?([0-9,]+\.?\d{0,2})",
                r"grand\s*total\s*:?\s*₹?\$?€?£?([0-9,]+\.?\d{0,2})",
                r"net\s*amount\s*:?\s*₹?\$?€?£?([0-9,]+\.?\d{0,2})",
                r"balance\s*due\s*:?\s*₹?\$?€?£?([0-9,]+\.?\d{0,2})",
            ],
            "vendor": [
                # Company names with common business suffixes
                r"^([A-Z][A-Za-z\s&\.\-,]+(?:Inc|LLC|Corp|Ltd|Co|Company|Corporation|Limited|Pvt|Private|LLP|Partnership)\.?)",
                # Lines starting with capital letters (likely company names)
                r"^([A-Z][A-Za-z\s&\.\-,]{5,50})",
                # After "from" or "bill from"
                r"(?:from|bill\s*from)\s*:?\s*([A-Z][A-Za-z\s&\.\-,]+)",
                # After "vendor" or "supplier"
                r"(?:vendor|supplier)\s*:?\s*([A-Z][A-Za-z\s&\.\-,]+)",
            ],
            "vendor_address": [
                # Street addresses
                r"(\d+\s+[A-Za-z\s\.\-,]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd))",
                # PO Box addresses
                r"(P\.?O\.?\s*Box\s+\d+)",
                # General address patterns
                r"([A-Z][A-Za-z\s\.\-,]+,\s*[A-Z][A-Za-z\s]+,\s*\d{5,6})",
            ],
            "vendor_phone": [
                r"(?:phone|tel|mobile|contact)\s*:?\s*([+]?[\d\s\-\(\)]{10,15})",
                r"([+]?[\d\s\-\(\)]{10,15})",
            ],
            "vendor_email": [
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            ],
            "customer": [
                r"(?:bill\s*to|customer|client)\s*:?\s*([A-Z][A-Za-z\s&\.\-,]+)",
                r"(?:ship\s*to|deliver\s*to)\s*:?\s*([A-Z][A-Za-z\s&\.\-,]+)",
            ],
        }

    def extract_text_from_image(self, image_path):
        """Extract text from image using OCR"""
        try:
            # Preprocess image for better OCR
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply threshold to get better text recognition
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Use pytesseract to extract text
            text = pytesseract.image_to_string(thresh, config="--psm 6")
            return text
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF"""
        try:
            text = ""
            # Try direct text extraction first
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()

            # If no text found, convert to images and use OCR
            if not text.strip():
                images = convert_from_path(pdf_path)
                for i, image in enumerate(images):
                    # Save temporary image
                    temp_path = f"temp_page_{i}.png"
                    image.save(temp_path)
                    text += self.extract_text_from_image(temp_path)
                    os.remove(temp_path)

            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def extract_field(self, text, field_type):
        """Extract specific field from text using regex patterns"""
        if field_type == "vendor":
            return self._extract_vendor_name(text)
        
        text_lower = text.lower()
        for pattern in self.patterns.get(field_type, []):
            match = re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None
    
    def _extract_vendor_name(self, text):
        """Enhanced vendor name extraction from invoice header"""
        lines = text.split('\n')
        
        # Look for vendor name in first 10 lines (header area)
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Skip common header words
            skip_words = ['invoice', 'bill', 'receipt', 'tax', 'date', 'number', 'page']
            if any(word in line.lower() for word in skip_words):
                continue
            
            # Look for company indicators
            company_indicators = ['inc', 'llc', 'corp', 'ltd', 'co', 'company', 'corporation', 'limited', 'pvt', 'private']
            
            # Check if line contains company indicators or looks like a company name
            if (any(indicator in line.lower() for indicator in company_indicators) or
                (len(line) > 5 and line[0].isupper() and not line.isdigit())):
                
                # Clean up the company name
                cleaned_name = re.sub(r'[^\w\s&\.\-,]', '', line).strip()
                if len(cleaned_name) > 3:
                    return cleaned_name
        
        # Fallback to regex patterns
        for pattern in self.patterns.get("vendor", []):
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None

    def extract_line_items(self, text):
        """Extract line items from invoice text with enhanced structure"""
        lines = text.split("\n")
        line_items = []
        
        # Enhanced patterns for different invoice formats
        patterns = [
            # Pattern 1: Qty Description Amount (standard format)
            r"^(\d+(?:\.\d+)?)\s+(.+?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$",
            
            # Pattern 2: Description Qty Unit_Price Total
            r"^(.+?)\s+(\d+(?:\.\d+)?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$",
            
            # Pattern 3: Product codes with descriptions
            r"^([A-Z0-9\-]+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$",
            
            # Pattern 4: Tax lines (GST, VAT, etc.)
            r"^(.+?(?:GST|VAT|TAX|CGST|SGST|IGST|UTGST).*?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$",
            
            # Pattern 5: Service charges, fees, discounts
            r"^(.+?(?:charge|fee|discount|shipping|handling|delivery).*?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$",
            
            # Pattern 6: Simple amount at end of line
            r"^(.+?)\s+(?:₹|€|£)?([0-9,]+\.?\d{0,2})$"
        ]
        
        # Skip patterns (headers, footers, etc.)
        skip_patterns = [
            r"^(qty|quantity|description|amount|total|subtotal|item|product).*$",
            r"^(invoice|bill|receipt|order).*$",
            r"^(page|continued|terms|conditions).*$",
            r"^(thank you|thanks|signature|authorized).*$",
            r"^\s*[-=_]+\s*$",  # separator lines
            r"^\s*\d+\s*$",  # lone numbers
        ]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and very short lines
            if not line or len(line) < 5:
                continue
                
            # Skip header/footer patterns
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Try each pattern
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    item = self._parse_line_item(match, i + 1, line)
                    if item and self._validate_line_item(item):
                        line_items.append(item)
                    break
        
        # Post-process and categorize items
        return self._categorize_line_items(line_items)
    
    def _parse_line_item(self, match, pattern_type, original_line):
        """Parse matched line item based on pattern type"""
        try:
            if pattern_type == 1:  # Qty Description Amount
                return {
                    "item_type": "product",
                    "quantity": float(match.group(1)),
                    "description": self._clean_description(match.group(2)),
                    "unit_price": None,
                    "amount": self._clean_amount(match.group(3)),
                    "original_line": original_line
                }
            
            elif pattern_type == 2:  # Description Qty Unit_Price Total
                return {
                    "item_type": "product",
                    "quantity": float(match.group(2)),
                    "description": self._clean_description(match.group(1)),
                    "unit_price": self._clean_amount(match.group(3)),
                    "amount": self._clean_amount(match.group(4)),
                    "original_line": original_line
                }
            
            elif pattern_type == 3:  # Product code Description Qty Amount
                return {
                    "item_type": "product",
                    "product_code": match.group(1),
                    "quantity": float(match.group(3)),
                    "description": self._clean_description(match.group(2)),
                    "unit_price": None,
                    "amount": self._clean_amount(match.group(4)),
                    "original_line": original_line
                }
            
            elif pattern_type == 4:  # Tax lines
                return {
                    "item_type": "tax",
                    "quantity": 1,
                    "description": self._clean_description(match.group(1)),
                    "unit_price": None,
                    "amount": self._clean_amount(match.group(2)),
                    "original_line": original_line
                }
            
            elif pattern_type == 5:  # Service charges
                return {
                    "item_type": "service",
                    "quantity": 1,
                    "description": self._clean_description(match.group(1)),
                    "unit_price": None,
                    "amount": self._clean_amount(match.group(2)),
                    "original_line": original_line
                }
            
            elif pattern_type == 6:  # Generic amount
                return {
                    "item_type": "other",
                    "quantity": 1,
                    "description": self._clean_description(match.group(1)),
                    "unit_price": None,
                    "amount": self._clean_amount(match.group(2)),
                    "original_line": original_line
                }
                
        except (ValueError, IndexError):
            return None
        
        return None
    
    def _clean_description(self, description):
        """Clean and normalize description text"""
        if not description:
            return ""
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common prefixes/suffixes
        description = re.sub(r'^(item|product|service):\s*', '', description, flags=re.IGNORECASE)
        
        # Capitalize first letter
        if description:
            description = description[0].upper() + description[1:]
        
        return description
    
    def _clean_amount(self, amount_str):
        """Clean and convert amount to float"""
        if not amount_str:
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d\.-]', '', str(amount_str))
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _validate_line_item(self, item):
        """Validate if the extracted item makes sense"""
        if not item or not item.get('description'):
            return False
        
        # Check if amount is reasonable
        amount = item.get('amount', 0)
        if amount < 0 or amount > 999999:  # Reasonable limits
            return False
        
        # Check if quantity is reasonable
        quantity = item.get('quantity', 0)
        if quantity < 0 or quantity > 10000:  # Reasonable limits
            return False
        
        # Skip very short descriptions
        if len(item.get('description', '')) < 3:
            return False
        
        return True
    
    def _categorize_line_items(self, items):
        """Categorize and structure line items for better presentation"""
        categorized = {
            "products": [],
            "services": [],
            "taxes": [],
            "discounts": [],
            "other": [],
            "summary": {
                "total_items": len(items),
                "subtotal": 0.0,
                "tax_total": 0.0,
                "grand_total": 0.0
            }
        }
        
        for item in items:
            item_type = item.get('item_type', 'other')
            amount = item.get('amount', 0.0)
            
            # Categorize based on type and description
            if item_type == 'tax' or any(tax_word in item.get('description', '').lower() 
                                       for tax_word in ['gst', 'vat', 'tax', 'cgst', 'sgst', 'igst', 'utgst']):
                categorized['taxes'].append(item)
                categorized['summary']['tax_total'] += amount
                
            elif 'discount' in item.get('description', '').lower() or amount < 0:
                categorized['discounts'].append(item)
                
            elif item_type == 'service' or any(service_word in item.get('description', '').lower() 
                                             for service_word in ['shipping', 'delivery', 'handling', 'fee', 'charge']):
                categorized['services'].append(item)
                categorized['summary']['subtotal'] += amount
                
            elif item_type == 'product':
                categorized['products'].append(item)
                categorized['summary']['subtotal'] += amount
                
            else:
                categorized['other'].append(item)
                categorized['summary']['subtotal'] += amount
        
        # Calculate grand total
        categorized['summary']['grand_total'] = (
            categorized['summary']['subtotal'] + 
            categorized['summary']['tax_total']
        )
        
        # For backward compatibility, also return flat list
        all_items = []
        for category in ['products', 'services', 'taxes', 'discounts', 'other']:
            all_items.extend(categorized[category])
        
        # Add categorized data to each item for template use
        for item in all_items:
            item['formatted_amount'] = f"₹{item.get('amount', 0):.2f}"
            item['formatted_quantity'] = f"{item.get('quantity', 0):.0f}" if item.get('quantity', 0) == int(item.get('quantity', 0)) else f"{item.get('quantity', 0):.2f}"
        
        return all_items

    def process_invoice(self, file_path):
        """Main method to process invoice and extract all details with AI enhancement"""
        file_ext = os.path.splitext(file_path)[1].lower()

        # Extract text based on file type
        if file_ext == ".pdf":
            text = self.extract_text_from_pdf(file_path)
        else:
            text = self.extract_text_from_image(file_path)

        if not text:
            return None

        # Try Gemini AI extraction first
        structured_data, extraction_method = self._extract_with_ai_fallback(text)
        
        if structured_data:
            # Convert structured data to legacy format for backward compatibility
            invoice_data = structured_data.get_legacy_format()
            invoice_data["raw_text"] = text
            return invoice_data
        else:
            # Fallback to regex-only extraction
            return self._extract_with_regex_only(text)
    
    def _extract_with_ai_fallback(self, text):
        """Extract data using AI with fallback to regex."""
        # Try Gemini AI extraction if available
        if self.gemini_extractor.is_available():
            try:
                structured_data, method = self.gemini_extractor.extract(text)
                if structured_data and structured_data.extraction_metadata.confidence_score > 0.3:
                    logging.info(f"Successfully extracted data using Gemini AI (confidence: {structured_data.extraction_metadata.confidence_score:.2f})")
                    return structured_data, method
                else:
                    logging.warning(f"Gemini AI extraction had low confidence ({structured_data.extraction_metadata.confidence_score:.2f} if structured_data else 'None'), falling back to regex")
            except Exception as e:
                logging.error(f"Gemini AI extraction error: {e}")
        else:
            logging.warning("Gemini AI not available, using regex fallback")
        
        # Fallback to regex extraction
        if config.ai.fallback_enabled:
            logging.info("Using enhanced regex fallback extraction")
            return self._convert_regex_to_structured(text), "regex_fallback"
        
        return None, "extraction_failed"
    
    def force_ai_extraction(self, file_path):
        """Force AI extraction without regex fallback for testing."""
        file_ext = os.path.splitext(file_path)[1].lower()

        # Extract text based on file type
        if file_ext == ".pdf":
            text = self.extract_text_from_pdf(file_path)
        else:
            text = self.extract_text_from_image(file_path)

        if not text:
            return None

        # Force AI extraction only
        if self.gemini_extractor.is_available():
            try:
                structured_data, method = self.gemini_extractor.extract(text)
                if structured_data:
                    invoice_data = structured_data.get_legacy_format()
                    invoice_data["raw_text"] = text
                    return invoice_data
            except Exception as e:
                logging.error(f"Forced AI extraction failed: {e}")
        
        return None
    
    def _extract_with_regex_only(self, text):
        """Legacy regex-only extraction for backward compatibility."""
        invoice_data = {
            "invoice_number": self.extract_field(text, "invoice_number"),
            "date": self.extract_field(text, "date"),
            "vendor": self.extract_field(text, "vendor"),
            "total": self.extract_field(text, "total"),
            "line_items": self.extract_line_items(text),
            "raw_text": text,
            "processed_at": datetime.now().isoformat(),
            "extraction_method": "regex_only"
        }

        # Clean up the data
        if invoice_data["date"]:
            try:
                parsed_date = parser.parse(invoice_data["date"])
                invoice_data["date"] = parsed_date.strftime("%Y-%m-%d")
            except:
                pass

        if invoice_data["total"]:
            # Clean up total amount
            invoice_data["total"] = re.sub(r"[^\d\.]", "", invoice_data["total"])

        return invoice_data
    
    def _convert_regex_to_structured(self, text):
        """Convert regex extraction results to structured format with enhanced extraction."""
        # Extract basic fields using regex
        invoice_number = self.extract_field(text, "invoice_number")
        date = self.extract_field(text, "date")
        vendor_name = self.extract_field(text, "vendor")
        total = self.extract_field(text, "total")
        line_items = self.extract_line_items(text)
        
        # Extract additional vendor information
        vendor_address = self.extract_field(text, "vendor_address")
        vendor_phone = self.extract_field(text, "vendor_phone")
        vendor_email = self.extract_field(text, "vendor_email")
        customer_name = self.extract_field(text, "customer")
        
        # Create structured data object
        structured_data = StructuredInvoiceData()
        
        # Set extraction metadata
        structured_data.extraction_metadata.method = "regex_fallback"
        structured_data.extraction_metadata.fallback_used = True
        structured_data.extraction_metadata.confidence_score = 0.6  # Lower confidence for regex
        
        # Set basic invoice metadata
        structured_data.invoice_metadata.invoice_number = invoice_number
        if date:
            try:
                parsed_date = parser.parse(date)
                structured_data.invoice_metadata.invoice_date = parsed_date.strftime("%Y-%m-%d")
            except:
                structured_data.invoice_metadata.invoice_date = date
        
        # Detect currency from text
        currency_patterns = {
            r'₹': 'INR',
            r'\$': 'USD', 
            r'€': 'EUR',
            r'£': 'GBP'
        }
        for pattern, currency in currency_patterns.items():
            if re.search(pattern, text):
                structured_data.invoice_metadata.currency = currency
                break
        
        # Set vendor details with enhanced extraction
        structured_data.vendor_details.name = vendor_name
        if vendor_email:
            structured_data.vendor_details.contact.email = vendor_email
        if vendor_phone:
            structured_data.vendor_details.contact.phone = vendor_phone
        
        # Parse vendor address if found
        if vendor_address:
            # Try to parse address components
            address_parts = vendor_address.split(',')
            if len(address_parts) >= 1:
                structured_data.vendor_details.address.street = address_parts[0].strip()
            if len(address_parts) >= 2:
                structured_data.vendor_details.address.city = address_parts[1].strip()
            if len(address_parts) >= 3:
                # Look for postal code in the last part
                last_part = address_parts[-1].strip()
                postal_match = re.search(r'\b\d{5,6}\b', last_part)
                if postal_match:
                    structured_data.vendor_details.address.postal_code = postal_match.group()
                    # Remove postal code from state/country
                    state_country = re.sub(r'\b\d{5,6}\b', '', last_part).strip()
                    if state_country:
                        structured_data.vendor_details.address.state = state_country
        
        # Set customer details
        if customer_name:
            structured_data.customer_details.name = customer_name
        
        # Convert line items to structured format
        from structured_data import LineItem
        for item in line_items:
            line_item = LineItem(
                description=item.get('description', ''),
                quantity=item.get('quantity', 1),
                unit_price=item.get('unit_price'),
                subtotal=item.get('amount', 0),
                total=item.get('amount', 0),
                category=item.get('item_type', 'other')
            )
            line_item.calculate_totals()
            structured_data.line_items.append(line_item)
        
        # Set summary with better total extraction
        if total:
            try:
                total_amount = float(re.sub(r"[^\d\.]", "", total))
                structured_data.summary.grand_total = total_amount
            except:
                pass
        
        # Try to extract tax information from line items
        tax_items = [item for item in line_items if 'tax' in item.get('description', '').lower() or item.get('item_type') == 'tax']
        if tax_items:
            structured_data.summary.total_tax = sum(item.get('amount', 0) for item in tax_items)
        
        # Calculate all totals
        structured_data.calculate_all_totals()
        
        return structured_data


# Initialize the processor
processor = InvoiceProcessor()


@app.route("/")
def index():
    # Get list of processed invoices
    processed_invoices = []
    if os.path.exists(app.config["PROCESSED_FOLDER"]):
        for filename in os.listdir(app.config["PROCESSED_FOLDER"]):
            if filename.endswith(".json"):
                file_path = os.path.join(app.config["PROCESSED_FOLDER"], filename)
                try:
                    with open(file_path, "r") as f:
                        invoice_data = json.load(f)

                    file_stats = os.stat(file_path)
                    processed_invoices.append(
                        {
                            "id": filename.replace(".json", ""),
                            "original_filename": invoice_data.get(
                                "original_filename", "Unknown"
                            ),
                            "invoice_number": invoice_data.get("invoice_number", "N/A"),
                            "vendor": invoice_data.get("vendor", "N/A"),
                            "date": invoice_data.get("date", "N/A"),
                            "total": invoice_data.get("total", "N/A"),
                            "processed": datetime.fromtimestamp(
                                file_stats.st_mtime
                            ).strftime("%d %b %Y"),
                            "line_items_count": len(invoice_data.get("line_items", [])),
                        }
                    )
                except Exception as e:
                    print(f"Error reading processed file {filename}: {e}")

    return render_template("index.html", invoices=processed_invoices)



@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "GET":
        # Redirect GET requests to the main page
        return redirect(url_for("index"))
    if "file" not in request.files:
        flash("No file selected", "error")
        return redirect(request.url)

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("index"))

    if file and allowed_file(file.filename):
        # Generate unique filename to prevent conflicts
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)

        # Process the invoice
        try:
            invoice_data = processor.process_invoice(file_path)
            if invoice_data:
                # Save processed data
                processed_filename = f"{name}_{uuid.uuid4().hex[:8]}.json"
                processed_path = os.path.join(
                    app.config["PROCESSED_FOLDER"], processed_filename
                )

                # Add file info to invoice data
                invoice_data["original_filename"] = original_filename
                invoice_data["file_path"] = unique_filename
                invoice_data["processed_filename"] = processed_filename

                with open(processed_path, "w") as f:
                    json.dump(invoice_data, f, indent=2)

                flash(
                    f'Invoice "{original_filename}" processed successfully!', "success"
                )
            else:
                flash(
                    f'File uploaded but could not extract invoice data from "{original_filename}"',
                    "warning",
                )
        except Exception as e:
            flash(f"File uploaded but processing failed: {str(e)}", "warning")

    else:
        flash("Invalid file type. Please upload PDF or image files only.", "error")

    return redirect(url_for("index"))


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"], filename, as_attachment=True
    )


@app.route("/delete/<filename>")
def delete_file(filename):
    try:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash("File deleted successfully!", "success")
        else:
            flash("File not found!", "error")
    except Exception:
        flash("Error deleting file!", "error")

    return redirect(url_for("index"))


# API Endpoints
@app.route("/api/invoices", methods=["POST"])
def api_upload_invoice():
    """API endpoint to upload and process invoice"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        # Save file
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)

        # Process invoice
        try:
            invoice_data = processor.process_invoice(file_path)
            if invoice_data:
                # Save processed data
                processed_filename = f"{name}_{uuid.uuid4().hex[:8]}.json"
                processed_path = os.path.join(
                    app.config["PROCESSED_FOLDER"], processed_filename
                )

                invoice_data["original_filename"] = original_filename
                invoice_data["file_path"] = unique_filename
                invoice_data["processed_filename"] = processed_filename
                invoice_data["id"] = processed_filename.replace(".json", "")

                with open(processed_path, "w") as f:
                    json.dump(invoice_data, f, indent=2)

                return jsonify(
                    {
                        "success": True,
                        "message": "Invoice processed successfully",
                        "data": invoice_data,
                    }
                ), 200
            else:
                return jsonify(
                    {"success": False, "message": "Could not extract invoice data"}
                ), 400
        except Exception as e:
            return jsonify(
                {"success": False, "message": f"Processing failed: {str(e)}"}
            ), 500
    else:
        return jsonify({"error": "Invalid file type"}), 400


@app.route("/api/invoices/<invoice_id>")
def api_get_invoice(invoice_id):
    """API endpoint to get processed invoice data"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Invoice not found"}), 404

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        return jsonify(invoice_data), 200
    except Exception as e:
        return jsonify({"error": f"Error reading invoice: {str(e)}"}), 500


@app.route("/api/invoices")
def api_list_invoices():
    """API endpoint to list all processed invoices"""
    invoices = []
    if os.path.exists(app.config["PROCESSED_FOLDER"]):
        for filename in os.listdir(app.config["PROCESSED_FOLDER"]):
            if filename.endswith(".json"):
                file_path = os.path.join(app.config["PROCESSED_FOLDER"], filename)
                try:
                    with open(file_path, "r") as f:
                        invoice_data = json.load(f)

                    invoices.append(
                        {
                            "id": filename.replace(".json", ""),
                            "invoice_number": invoice_data.get("invoice_number"),
                            "vendor": invoice_data.get("vendor"),
                            "date": invoice_data.get("date"),
                            "total": invoice_data.get("total"),
                            "processed_at": invoice_data.get("processed_at"),
                            "extraction_method": invoice_data.get("extraction_method", "unknown"),
                        }
                    )
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

    return jsonify(invoices), 200


@app.route("/api/debug/ai-status")
def api_ai_status():
    """API endpoint to check AI extraction status"""
    return jsonify({
        "ai_available": processor.gemini_extractor.is_available(),
        "ai_configured": processor.gemini_extractor.config.is_configured(),
        "ai_enabled": processor.gemini_extractor.config.enabled,
        "fallback_enabled": config.ai.fallback_enabled,
        "config": processor.gemini_extractor.get_usage_info(),
        "api_key_present": bool(processor.gemini_extractor.config.api_key),
        "model": processor.gemini_extractor.config.model
    }), 200


@app.route("/api/accounting/entries", methods=["POST"])
def api_accounting_integration():
    """Enhanced accounting integration endpoint with structured line items"""
    data = request.get_json()

    # Extract structured data
    invoice_data = data.get('invoice_data', {})
    structured_items = data.get('structured_items', [])
    accounting_format = data.get('accounting_format', {})

    # Process line items for accounting
    accounting_entries = []
    
    for item in structured_items:
        entry = {
            "type": item.get('item_type', 'other'),
            "description": item.get('description', ''),
            "quantity": item.get('quantity', 1),
            "unit_price": item.get('unit_price'),
            "amount": item.get('amount', 0),
            "account_code": get_account_code(item.get('item_type', 'other')),
            "tax_code": get_tax_code(item) if item.get('item_type') == 'tax' else None
        }
        accounting_entries.append(entry)

    # Mock processing - in real implementation, this would integrate with accounting software
    response = {
        "success": True,
        "message": "Invoice with structured line items processed successfully",
        "entry_id": f"ACC_{uuid.uuid4().hex[:8].upper()}",
        "entries_processed": len(accounting_entries),
        "accounting_entries": accounting_entries,
        "totals": accounting_format.get('totals', {}),
        "data": data,
    }

    return jsonify(response), 201


@app.route("/api/invoices/test-ai", methods=["POST"])
def api_test_ai_extraction():
    """API endpoint to test AI extraction specifically"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        # Save file temporarily
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"test_{name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)

        try:
            # Force AI extraction
            ai_result = processor.force_ai_extraction(file_path)
            
            # Also try regular extraction for comparison
            regular_result = processor.process_invoice(file_path)
            
            # Clean up test file
            os.remove(file_path)
            
            return jsonify({
                "success": True,
                "ai_extraction": ai_result,
                "regular_extraction": regular_result,
                "ai_available": processor.gemini_extractor.is_available(),
                "ai_config": processor.gemini_extractor.get_usage_info()
            }), 200
            
        except Exception as e:
            # Clean up test file
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": f"Extraction test failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file type"}), 400


@app.route("/api/invoices/<invoice_id>/line-items/accounting", methods=["POST"])
def api_push_line_items_to_accounting(invoice_id):
    """Push only line items to accounting system"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Invoice not found"}), 404

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        
        line_items = invoice_data.get('line_items', [])
        
        # Create accounting entries for each line item
        entries_created = []
        for i, item in enumerate(line_items):
            entry_id = f"LI_{uuid.uuid4().hex[:6].upper()}"
            entry = {
                "entry_id": entry_id,
                "invoice_id": invoice_id,
                "line_item_index": i,
                "type": item.get('item_type', 'other'),
                "description": item.get('description', ''),
                "amount": item.get('amount', 0),
                "account_code": get_account_code(item.get('item_type', 'other'))
            }
            entries_created.append(entry)

        return jsonify({
            "success": True,
            "message": "Line items pushed to accounting successfully",
            "entries_created": len(entries_created),
            "entries": entries_created
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error processing line items: {str(e)}"}), 500


@app.route("/api/invoices/<invoice_id>/line-items/<int:item_index>/accounting", methods=["POST"])
def api_push_single_item_to_accounting(invoice_id, item_index):
    """Push single line item to accounting system"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Invoice not found"}), 404

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        
        line_items = invoice_data.get('line_items', [])
        
        if item_index >= len(line_items):
            return jsonify({"error": "Line item not found"}), 404
        
        item = line_items[item_index]
        entry_id = f"SI_{uuid.uuid4().hex[:6].upper()}"
        
        entry = {
            "entry_id": entry_id,
            "invoice_id": invoice_id,
            "line_item_index": item_index,
            "type": item.get('item_type', 'other'),
            "description": item.get('description', ''),
            "amount": item.get('amount', 0),
            "account_code": get_account_code(item.get('item_type', 'other')),
            "processed_at": datetime.now().isoformat()
        }

        return jsonify({
            "success": True,
            "message": "Line item pushed to accounting successfully",
            "entry_id": entry_id,
            "entry": entry
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error processing line item: {str(e)}"}), 500


@app.route("/api/invoices/<invoice_id>/line-items/export")
def api_export_line_items(invoice_id):
    """Export line items as structured JSON"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Invoice not found"}), 404

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        
        line_items = invoice_data.get('line_items', [])
        
        # Create enhanced export format
        export_data = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_data.get('invoice_number'),
            "vendor": invoice_data.get('vendor'),
            "date": invoice_data.get('date'),
            "export_timestamp": datetime.now().isoformat(),
            "line_items": line_items,
            "summary": {
                "total_items": len(line_items),
                "categories": categorize_items_summary(line_items),
                "totals": calculate_line_items_totals(line_items)
            }
        }

        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_id}_line_items.json'
        return response

    except Exception as e:
        return jsonify({"error": f"Error exporting line items: {str(e)}"}), 500


def get_account_code(item_type):
    """Get accounting account code based on item type"""
    account_codes = {
        'product': '4000',  # Sales Revenue
        'service': '4100',  # Service Revenue
        'tax': '2200',      # Tax Payable
        'discount': '4900', # Discounts Given
        'other': '4999'     # Miscellaneous Revenue
    }
    return account_codes.get(item_type, '4999')


def get_tax_code(item):
    """Get tax code based on item description"""
    description = item.get('description', '').lower()
    if 'gst' in description or 'vat' in description:
        return 'GST'
    elif 'sales tax' in description:
        return 'ST'
    return 'TAX'


def categorize_items_summary(line_items):
    """Create summary of items by category"""
    categories = {}
    for item in line_items:
        item_type = item.get('item_type', 'other')
        if item_type not in categories:
            categories[item_type] = {'count': 0, 'total_amount': 0}
        categories[item_type]['count'] += 1
        categories[item_type]['total_amount'] += item.get('amount', 0)
    return categories


def calculate_line_items_totals(line_items):
    """Calculate various totals from line items"""
    totals = {
        'subtotal': 0,
        'tax_total': 0,
        'discount_total': 0,
        'grand_total': 0
    }
    
    for item in line_items:
        amount = item.get('amount', 0)
        item_type = item.get('item_type', 'other')
        
        if item_type in ['product', 'service']:
            totals['subtotal'] += amount
        elif item_type == 'tax':
            totals['tax_total'] += amount
        elif item_type == 'discount' or amount < 0:
            totals['discount_total'] += abs(amount)
        
        totals['grand_total'] += amount
    
    return totals


@app.route("/invoice/<invoice_id>")
def view_invoice(invoice_id):
    """View detailed invoice page with structured data support"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        flash("Invoice not found!", "error")
        return redirect(url_for("index"))

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        
        # Add invoice ID for JavaScript functions
        invoice_data["id"] = invoice_id
        
        # Use structured template if structured data is available
        if invoice_data.get("structured_data"):
            return render_template("invoice_detail_structured.html", invoice=invoice_data)
        else:
            return render_template("invoice_detail.html", invoice=invoice_data)
            
    except Exception as e:
        flash(f"Error loading invoice: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/download/json/<invoice_id>")
def download_invoice_json(invoice_id):
    """Download invoice data as JSON file"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        flash("Invoice not found!", "error")
        return redirect(url_for("index"))

    try:
        return send_from_directory(
            app.config["PROCESSED_FOLDER"],
            f"{invoice_id}.json",
            as_attachment=True,
            download_name=f"invoice_{invoice_id}.json",
        )
    except Exception as e:
        flash(f"Error downloading invoice: {str(e)}", "error")
        return redirect(url_for("view_invoice", invoice_id=invoice_id))


@app.route("/api/invoices/<invoice_id>/accounting-json")
def api_download_accounting_json(invoice_id):
    """Download structured accounting JSON"""
    file_path = os.path.join(app.config["PROCESSED_FOLDER"], f"{invoice_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Invoice not found"}), 404

    try:
        with open(file_path, "r") as f:
            invoice_data = json.load(f)
        
        accounting_json = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_data.get('invoice_number'),
            "date": invoice_data.get('date'),
            "vendor": invoice_data.get('vendor'),
            "product_name": invoice_data.get('product_name'),
            "amount": invoice_data.get('total'),
            "tax": invoice_data.get('tax'),
            "address": invoice_data.get('address'),
            "processed_at": datetime.now().isoformat(),
            "accounting_entries": {
                "debit": {
                    "account": "Accounts Receivable",
                    "account_code": "1200",
                    "amount": float(invoice_data.get('total', 0))
                },
                "credit": {
                    "account": "Sales Revenue",
                    "account_code": "4000", 
                    "amount": float(invoice_data.get('total', 0))
                }
            },
            "extracted_data": {
                "invoice_number": invoice_data.get('invoice_number'),
                "date": invoice_data.get('date'),
                "vendor": invoice_data.get('vendor'),
                "total": invoice_data.get('total'),
                "raw_text": invoice_data.get('raw_text')
            }
        }

        response = jsonify(accounting_json)
        response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_id}_accounting.json'
        return response

    except Exception as e:
        return jsonify({"error": f"Error generating accounting JSON: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=7890)

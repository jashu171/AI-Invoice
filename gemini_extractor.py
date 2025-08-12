"""
Gemini AI extractor for structured invoice data extraction.
Uses Google's Gemini AI to intelligently extract and structure invoice information.
"""

import json
import time
import logging
from typing import Optional, Tuple, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from config import config
from structured_data import StructuredInvoiceData, ExtractionMetadata

logger = logging.getLogger(__name__)


class GeminiAIExtractor:
    """Gemini AI-powered invoice data extractor."""
    
    def __init__(self):
        self.config = config.ai
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
       
        if not self.config.is_configured():
            logger.warning("Gemini AI not configured, extraction will be disabled")
            return
        
        try:
            genai.configure(api_key=self.config.api_key)
            
            # Configure safety settings to be more permissive for business documents
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            generation_config = {
                "temperature": self.config.temperature,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": self.config.max_tokens,
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.config.model,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info(f"Gemini AI model initialized: {self.config.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI model: {e}")
            self.model = None    
 
    def _create_extraction_prompt(self, text: str) -> str:
        """Create the prompt for structured invoice extraction."""
        return f"""You are an expert invoice data extraction AI. Extract ALL available information from this invoice text with maximum accuracy and completeness.

CRITICAL INSTRUCTIONS:
1. Extract COMPLETE company names, addresses, and contact information
2. Look for vendor/supplier information at the top of the invoice
3. Look for customer/bill-to information in the middle section
4. Extract ALL line items with descriptions, quantities, and amounts
5. Calculate accurate totals and tax information
6. If information is partially visible or unclear, extract what you can see
7. Pay special attention to company names - extract the full business name, not just partial text

Return ONLY valid JSON in this exact structure:

{{
  "invoice_metadata": {{
    "invoice_number": "extract invoice/bill number",
    "invoice_date": "YYYY-MM-DD format",
    "due_date": "YYYY-MM-DD format or null", 
    "po_number": "purchase order number or null",
    "currency": "USD/EUR/GBP/INR etc",
    "language": "detected language code"
  }},
  "vendor_details": {{
    "name": "COMPLETE company/business name",
    "address": {{
      "street": "full street address",
      "city": "city name",
      "state": "state/province", 
      "postal_code": "zip/postal code",
      "country": "country name"
    }},
    "contact": {{
      "phone": "phone number with country code if available",
      "email": "email address",
      "website": "website URL"
    }},
    "tax_id": "tax ID/GST number/VAT number"
  }},
  "customer_details": {{
    "name": "customer/bill-to company or person name",
    "address": {{
      "street": "customer street address",
      "city": "customer city",
      "state": "customer state", 
      "postal_code": "customer postal code",
      "country": "customer country"
    }},
    "contact": {{
      "phone": "customer phone",
      "email": "customer email"
    }}
  }},
  "line_items": [
    {{
      "description": "complete item description",
      "quantity": 1.0,
      "unit_price": 100.00,
      "subtotal": 100.00,
      "tax_rate": 0.18,
      "tax_amount": 18.00,
      "total": 118.00,
      "category": "product/service/tax/discount/shipping/other"
    }}
  ],
  "summary": {{
    "subtotal": 0.00,
    "total_tax": 0.00,
    "discounts": 0.00,
    "shipping": 0.00,
    "grand_total": 0.00
  }},
  "payment_terms": {{
    "terms": "payment terms text",
    "payment_methods": ["cash", "check", "bank transfer"],
    "bank_details": {{
      "account_name": "bank account name",
      "account_number": "account number",
      "routing_number": "routing/sort code",
      "iban": "IBAN code"
    }}
  }},
  "additional_info": {{
    "notes": "any additional notes or comments",
    "terms_conditions": "terms and conditions text",
    "reference_numbers": ["reference numbers found"]
  }}
}}

INVOICE TEXT TO ANALYZE:
{text}

Extract maximum information and return ONLY the JSON object:"""

    def extract(self, text: str) -> Tuple[Optional[StructuredInvoiceData], str]:
        """
        Extract structured data from invoice text using Gemini AI.
        
        Args:
            text: Raw invoice text from OCR
            
        Returns:
            Tuple of (StructuredInvoiceData or None, extraction_method)
        """
        if not self.model:
            logger.warning("Gemini AI model not available")
            return None, "model_unavailable"
        
        start_time = time.time()
        
        try:
            # Create the extraction prompt
            prompt = self._create_extraction_prompt(text)
            
            # Generate response with retry logic
            response = self._generate_with_retry(prompt)
            
            if not response:
                logger.error("No response from Gemini AI")
                return None, "no_response"
            
            # Parse the JSON response
            structured_data = self._parse_response(response, start_time)
            
            if structured_data:
                logger.info("Successfully extracted structured data with Gemini AI")
                return structured_data, "gemini_ai"
            else:
                logger.error("Failed to parse Gemini AI response")
                return None, "parse_error"
                
        except Exception as e:
            logger.error(f"Gemini AI extraction failed: {e}")
            return None, "extraction_error"
    
    def _generate_with_retry(self, prompt: str) -> Optional[str]:
        """Generate response with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                response = self.model.generate_content(prompt)
                
                if response.text:
                    return response.text.strip()
                else:
                    logger.warning(f"Empty response from Gemini AI (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.warning(f"Gemini AI request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None    
  
    def _parse_response(self, response_text: str, start_time: float) -> Optional[StructuredInvoiceData]:
        """Parse the JSON response from Gemini AI."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Create structured data object
            structured_data = StructuredInvoiceData.from_dict(data)
            
            # Calculate totals first
            structured_data.calculate_all_totals()
            
            # Set extraction metadata with dynamic confidence scoring
            processing_time = time.time() - start_time
            try:
                confidence_score = self._calculate_confidence_score(structured_data)
            except Exception as conf_error:
                logger.warning(f"Error calculating confidence score: {conf_error}")
                confidence_score = 0.5  # Default confidence
            
            structured_data.extraction_metadata = ExtractionMetadata(
                method="gemini_ai",
                model=self.config.model,
                confidence_score=confidence_score,
                processing_time=processing_time,
                fallback_used=False
            )
            
            # Validate the data
            try:
                validation_errors = structured_data.validate()
                if validation_errors:
                    logger.warning(f"Validation errors in extracted data: {validation_errors}")
                    structured_data.extraction_metadata.errors = validation_errors
            except Exception as val_error:
                logger.warning(f"Error during validation: {val_error}")
            
            return structured_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Gemini AI: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing Gemini AI response: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def is_available(self) -> bool:
        """Check if Gemini AI extraction is available."""
        return self.model is not None and self.config.is_configured()
    
    def _calculate_confidence_score(self, structured_data: StructuredInvoiceData) -> float:
        """Calculate confidence score based on extracted data completeness."""
        try:
            score = 0.0
            max_score = 10.0
            
            # Invoice metadata (2 points)
            if structured_data.invoice_metadata and structured_data.invoice_metadata.invoice_number:
                score += 1.0
            if structured_data.invoice_metadata and structured_data.invoice_metadata.invoice_date:
                score += 1.0
            
            # Vendor details (3 points)
            if structured_data.vendor_details and structured_data.vendor_details.name:
                score += 1.5
            if structured_data.vendor_details and structured_data.vendor_details.address and \
               (structured_data.vendor_details.address.street or structured_data.vendor_details.address.city):
                score += 1.0
            if structured_data.vendor_details and structured_data.vendor_details.contact and \
               (structured_data.vendor_details.contact.email or structured_data.vendor_details.contact.phone):
                score += 0.5
            
            # Line items (3 points)
            if structured_data.line_items and len(structured_data.line_items) > 0:
                score += 1.0
                # Bonus for detailed line items
                detailed_items = 0
                for item in structured_data.line_items:
                    if item and item.description and item.quantity is not None and item.quantity > 0:
                        detailed_items += 1
                if detailed_items > 0:
                    score += min(2.0, detailed_items * 0.5)
            
            # Summary totals (2 points)
            if structured_data.summary and structured_data.summary.grand_total is not None and structured_data.summary.grand_total > 0:
                score += 1.0
            if structured_data.summary and \
               ((structured_data.summary.subtotal is not None and structured_data.summary.subtotal > 0) or \
                (structured_data.summary.total_tax is not None and structured_data.summary.total_tax > 0)):
                score += 1.0
            
            return min(1.0, score / max_score)
        except Exception as e:
            logger.warning(f"Error in confidence calculation: {e}")
            return 0.5  # Default confidence
    
    def get_usage_info(self) -> Dict[str, Any]:
        """Get usage information and statistics."""
        return {
            "model": self.config.model,
            "enabled": self.config.enabled,
            "configured": self.config.is_configured(),
            "available": self.is_available(),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
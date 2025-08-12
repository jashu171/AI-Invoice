#!/usr/bin/env python3
"""
Test script to verify AI extraction is working properly.
"""

import os
import sys
from app import processor
from config import config

def test_ai_configuration():
    """Test AI configuration and availability."""
    print("=== AI Configuration Test ===")
    print(f"AI Enabled: {config.ai.enabled}")
    print(f"API Key Present: {bool(config.ai.api_key)}")
    print(f"Model: {config.ai.model}")
    print(f"Fallback Enabled: {config.ai.fallback_enabled}")
    print(f"AI Available: {processor.gemini_extractor.is_available()}")
    print(f"AI Configured: {processor.gemini_extractor.config.is_configured()}")
    
    if not processor.gemini_extractor.is_available():
        print("❌ AI extraction is not available!")
        return False
    else:
        print("✅ AI extraction is available!")
        return True

def test_sample_text():
    """Test AI extraction with sample invoice text."""
    print("\n=== Sample Text Extraction Test ===")
    
    sample_text = """
    ACME Corporation
    123 Business Street
    New York, NY 10001
    Phone: (555) 123-4567
    Email: billing@acme.com
    
    INVOICE
    
    Invoice Number: INV-2024-001
    Date: 2024-08-13
    
    Bill To:
    John Smith
    456 Customer Ave
    Los Angeles, CA 90210
    
    Description                 Qty    Price    Total
    Web Development Services     1    $2,500   $2,500.00
    Domain Registration          1      $15     $15.00
    Hosting (1 year)            1      $120    $120.00
    
    Subtotal:                                  $2,635.00
    Tax (8.5%):                                 $223.98
    Total:                                     $2,858.98
    """
    
    try:
        structured_data, method = processor.gemini_extractor.extract(sample_text)
        
        if structured_data:
            print(f"✅ Extraction successful using {method}")
            print(f"Confidence Score: {structured_data.extraction_metadata.confidence_score:.2f}")
            print(f"Vendor Name: {structured_data.vendor_details.name}")
            print(f"Invoice Number: {structured_data.invoice_metadata.invoice_number}")
            print(f"Total: {structured_data.summary.grand_total}")
            print(f"Line Items: {len(structured_data.line_items)}")
            
            if structured_data.vendor_details.address.street:
                print(f"Vendor Address: {structured_data.vendor_details.address.street}")
            if structured_data.vendor_details.contact.email:
                print(f"Vendor Email: {structured_data.vendor_details.contact.email}")
            
            return True
        else:
            print("❌ AI extraction returned no data")
            return False
            
    except Exception as e:
        print(f"❌ AI extraction failed: {e}")
        return False

def test_file_extraction():
    """Test extraction with actual files if available."""
    print("\n=== File Extraction Test ===")
    
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        print("No uploads directory found, skipping file test")
        return True
    
    files = [f for f in os.listdir(uploads_dir) if f.endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
    if not files:
        print("No test files found in uploads directory")
        return True
    
    # Test with first available file
    test_file = files[0]
    file_path = os.path.join(uploads_dir, test_file)
    
    print(f"Testing with file: {test_file}")
    
    try:
        # Test AI-only extraction
        ai_result = processor.force_ai_extraction(file_path)
        
        if ai_result:
            print("✅ AI extraction successful")
            print(f"Vendor: {ai_result.get('vendor', 'Not found')}")
            print(f"Invoice Number: {ai_result.get('invoice_number', 'Not found')}")
            print(f"Total: {ai_result.get('total', 'Not found')}")
            print(f"Extraction Method: {ai_result.get('extraction_method', 'Unknown')}")
            return True
        else:
            print("❌ AI extraction failed")
            return False
            
    except Exception as e:
        print(f"❌ File extraction test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting AI Extraction Tests...\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Configuration
    if test_ai_configuration():
        tests_passed += 1
    
    # Test 2: Sample text
    if test_sample_text():
        tests_passed += 1
    
    # Test 3: File extraction
    if test_file_extraction():
        tests_passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! AI extraction is working properly.")
        return 0
    else:
        print("❌ Some tests failed. Check the configuration and logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
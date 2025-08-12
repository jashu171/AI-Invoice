#!/usr/bin/env python3
"""
Simple test to check if AI extraction is working.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import config
    from gemini_extractor import GeminiAIExtractor
    
    print("=== AI Configuration Test ===")
    print(f"AI Enabled: {config.ai.enabled}")
    print(f"API Key Present: {bool(config.ai.api_key)}")
    print(f"Model: {config.ai.model}")
    
    # Initialize extractor
    extractor = GeminiAIExtractor()
    print(f"AI Available: {extractor.is_available()}")
    
    if extractor.is_available():
        print("✅ AI extraction is available!")
        
        # Test with sample text
        sample_text = """
        ACME Corporation
        123 Business Street
        New York, NY 10001
        
        INVOICE #INV-2024-001
        Date: 2024-08-13
        
        Bill To: John Smith
        
        Web Development Services    $2,500.00
        Total: $2,500.00
        """
        
        print("\n=== Testing AI Extraction ===")
        try:
            # First test the prompt generation
            prompt = extractor._create_extraction_prompt(sample_text)
            print(f"Prompt created successfully (length: {len(prompt)})")
            
            # Test the API call
            response = extractor._generate_with_retry(prompt)
            print(f"API Response received: {bool(response)}")
            if response:
                print(f"Response length: {len(response)}")
                print(f"Response preview: {response[:200]}...")
            
            # Test full extraction
            structured_data, method = extractor.extract(sample_text)
            
            if structured_data:
                print(f"✅ Extraction successful!")
                print(f"Method: {method}")
                print(f"Vendor: {structured_data.vendor_details.name}")
                print(f"Invoice Number: {structured_data.invoice_metadata.invoice_number}")
                print(f"Total: {structured_data.summary.grand_total}")
            else:
                print("❌ No data extracted")
                
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ AI extraction is not available")
        print("Check your GEMINI_API_KEY in .env file")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
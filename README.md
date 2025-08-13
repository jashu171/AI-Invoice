# Invoice Processing Application

A powerful Flask-based web application that automatically extracts and processes invoice data from PDF and image files using AI-powered OCR and Google's Gemini AI for intelligent data extraction.

## Features

- **Multi-format Support**: Process PDF documents and various image formats (PNG, JPG, JPEG, GIF, BMP, TIFF, WebP)
- **AI-Powered Extraction**: Uses Google Gemini AI for intelligent invoice data extraction with high accuracy
- **OCR Fallback**: Automatic fallback to regex-based extraction when AI is unavailable
- **Structured Data**: Extracts comprehensive invoice information including vendor details, line items, totals, and metadata
- **Web Interface**: Clean, responsive web interface for easy file upload and invoice management
- **Data Export**: Processed invoices saved as structured JSON files
- **Invoice Gallery**: View and manage all processed invoices with detailed information

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR engine
- Google Gemini API key (optional, for AI extraction)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd invoice-processing-app
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR**
   
   **macOS:**
   ```bash
   brew install tesseract
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install tesseract-ocr
   ```
   
   **Windows:**
   Download from: https://github.com/UB-Mannheim/tesseract/wiki

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Required for AI extraction (optional)
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Optional configurations
   SECRET_KEY=your-secure-secret-key
   DEBUG=false
   AI_EXTRACTION_ENABLED=true
   FALLBACK_TO_REGEX=true
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to: `http://localhost:5000`

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GEMINI_API_KEY` | Google Gemini API key for AI extraction | None | No* |
| `SECRET_KEY` | Flask secret key for sessions | `your-secret-key-here` | Yes |
| `DEBUG` | Enable debug mode | `false` | No |
| `AI_EXTRACTION_ENABLED` | Enable/disable AI extraction | `true` | No |
| `FALLBACK_TO_REGEX` | Enable regex fallback when AI fails | `true` | No |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.0-flash` | No |
| `GEMINI_TEMPERATURE` | AI model temperature (0-2) | `0.1` | No |
| `GEMINI_MAX_TOKENS` | Maximum tokens for AI response | `8192` | No |
| `UPLOAD_FOLDER` | Directory for uploaded files | `uploads` | No |
| `PROCESSED_FOLDER` | Directory for processed JSON files | `processed` | No |

*AI extraction is optional - the app will work with OCR + regex extraction if no API key is provided.

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Add the key to your `.env` file

## Usage

### Processing Invoices

1. **Upload Invoice**: Click "Choose File" and select a PDF or image file
2. **Automatic Processing**: The system will:
   - Extract text using OCR
   - Apply AI-powered data extraction (if configured)
   - Fall back to regex extraction if needed
   - Structure the data into a standardized format
3. **View Results**: Processed invoices appear in the main dashboard

### Supported File Formats

- **PDF Documents**: `.pdf`
- **Image Files**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`
- **Maximum File Size**: 16MB

### Extracted Data

The application extracts comprehensive invoice information:

#### Basic Information
- Invoice number
- Invoice date
- Due date
- Purchase order number
- Currency
- Language

#### Vendor Details
- Company name
- Complete address
- Contact information (phone, email, website)
- Tax ID/GST number

#### Customer Details
- Customer name
- Billing address
- Contact information

#### Line Items
- Product/service descriptions
- Quantities and unit prices
- Subtotals and tax amounts
- Item categories (product, service, tax, discount, shipping)

#### Financial Summary
- Subtotal
- Tax breakdown
- Discounts
- Shipping charges
- Grand total

#### Payment Information
- Payment terms
- Accepted payment methods
- Bank account details

## Project Structure

```
invoice-processing-app/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── gemini_extractor.py   # AI extraction logic
├── structured_data.py    # Data models and validation
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── uploads/              # Uploaded files (auto-created)
├── processed/            # Processed JSON files (auto-created)
├── static/               # CSS and JavaScript files
│   ├── css/
│   └── js/
├── templates/            # HTML templates
└── testing files/        # Test scripts
```

## API Endpoints

### Web Interface
- `GET /` - Main dashboard with processed invoices
- `POST /upload` - Upload and process invoice files
- `GET /invoice/<id>` - View detailed invoice information
- `GET /invoice/<id>/structured` - View structured data format

### File Management
- `GET /uploads/<filename>` - Access uploaded files
- `GET /processed/<filename>` - Access processed JSON files

## Data Format

Processed invoices are saved as JSON files with the following structure:

```json
{
  "invoice_number": "INV-001",
  "date": "2024-01-15",
  "vendor": "Company Name",
  "total": "1250.00",
  "line_items": [...],
  "processed_at": "2024-01-15T10:30:00",
  "extraction_method": "gemini_ai",
  "structured_data": {
    "invoice_metadata": {...},
    "vendor_details": {...},
    "customer_details": {...},
    "line_items": [...],
    "summary": {...}
  }
}
```

## Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Ensure Tesseract is installed and in your PATH
   - On macOS: `brew install tesseract`
   - On Ubuntu: `sudo apt-get install tesseract-ocr`

2. **Poor OCR results**
   - Ensure images are high quality and well-lit
   - PDFs with embedded text work better than scanned images
   - Try preprocessing images (contrast, brightness) before upload

3. **AI extraction not working**
   - Verify your `GEMINI_API_KEY` is correct
   - Check your Google Cloud billing is enabled
   - Ensure you have API quota remaining

4. **File upload fails**
   - Check file size (max 16MB)
   - Verify file format is supported
   - Ensure sufficient disk space

### Logs and Debugging

Enable debug mode by setting `DEBUG=true` in your `.env` file. This will provide detailed error messages and logging information.

## Development

### Running Tests

```bash
# Run AI extraction tests
python testing\ files/test_ai_extraction.py

# Run simple AI tests
python testing\ files/simple_ai_test.py
```

### Adding New Features

1. **Custom Extraction Rules**: Modify patterns in `app.py` `InvoiceProcessor` class
2. **New Data Fields**: Update `structured_data.py` data models
3. **UI Improvements**: Edit templates in `templates/` directory
4. **Styling**: Modify CSS files in `static/css/`

## Security Considerations

- Change the default `SECRET_KEY` in production
- Keep your Gemini API key secure and never commit it to version control
- Consider implementing file type validation beyond extensions
- Set up proper error handling for production deployment

## Performance Tips

- Use high-quality, well-lit images for better OCR results
- PDFs with embedded text process faster than scanned images
- Consider implementing file size limits based on your server capacity
- Monitor API usage to avoid exceeding Gemini API quotas

## License

This project is provided as-is for educational and commercial use. Please ensure you comply with Google's Gemini AI terms of service when using the AI extraction features.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the application logs when `DEBUG=true`
3. Ensure all dependencies are properly installed
4. Verify your environment configuration

---

**Happy Invoice Processing! 🧾✨**
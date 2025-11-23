# NLP and Image Processing Integration

## Overview

The bug reporting system now includes AI-powered Natural Language Processing (NLP) and image processing capabilities to enhance bug submissions.

## Features

### 1. Automatic Bug Analysis

When a user submits a bug report, the system automatically:
- Analyzes the bug description using GPT-4o-mini
- Suggests an appropriate bug category (if user selected "General")
- Provides relevant tags based on the description
- Assesses severity level

### 2. Screenshot Processing with Vision API

When a screenshot is attached to a bug report:
- OpenAI Vision API extracts text from the image (OCR)
- Analyzes visual elements, UI issues, and error messages
- Stores the extracted information in the `Issue.ocr` field

### 3. Real-time Bug Analysis API

A new API endpoint `/get-bug-analysis/` allows frontend applications to get analysis before submission:

**Endpoint:** `POST /get-bug-analysis/`

**Request Body:**
```json
{
  "description": "Bug description text",
  "url": "https://example.com/page"
}
```

**Response:**
```json
{
  "success": true,
  "suggested_category": "4",
  "tags": ["security", "xss", "web"],
  "severity": "high",
  "enhanced_description": "Detailed analysis of the bug"
}
```

## Technical Implementation

### NLP Analysis Function

```python
analyze_bug_with_nlp(description, url="")
```

This function:
- Takes a bug description and optional URL
- Calls GPT-4o-mini with a specialized prompt
- Returns analysis including category, tags, severity, and enhanced description
- Handles errors gracefully and logs them

### Image Processing Function

```python
process_screenshot_with_vision(screenshot_path)
```

This function:
- Takes the path to a screenshot file
- Resizes image if needed (max 1024x1024)
- Converts to base64 for API transmission
- Calls GPT-4o-mini vision model
- Returns extracted text and visual analysis

### Bug Submission Integration

The `submit_bug()` view has been enhanced to:
1. Call `analyze_bug_with_nlp()` for the description
2. Auto-suggest category if user selected "General" (0)
3. Process screenshot with `process_screenshot_with_vision()` after save
4. Store OCR results in `Issue.ocr` field

## Configuration

### Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for accessing GPT-4o-mini

### Model Used

- **Text Analysis:** `gpt-4o-mini` - Fast and cost-effective for text analysis
- **Vision Analysis:** `gpt-4o-mini` - Supports image understanding

## Error Handling

All NLP and image processing operations are wrapped in try-except blocks to ensure:
- Bug submission never fails due to AI processing errors
- Errors are logged for debugging
- Users can submit bugs even if AI features are unavailable

## Database Schema

### Issue Model Updates

The existing `Issue.ocr` field is now populated with:
```
Extracted Text:
[Text extracted from screenshot]

Visual Analysis:
[AI analysis of visual elements, errors, UI issues]
```

## Future Enhancements

Potential improvements:
- Frontend UI to display NLP suggestions before submission
- Tag auto-completion based on NLP analysis
- Duplicate detection using NLP similarity matching
- Multi-language support for OCR
- Custom model fine-tuning for better bug classification

## Testing

Run tests with:
```bash
python manage.py test website.tests.test_issues.NLPIntegrationTests
```

Tests cover:
- API endpoint authentication
- Description validation
- Success and error scenarios
- Mock OpenAI responses

## Performance Considerations

- NLP analysis adds ~1-3 seconds to bug submission
- Image processing adds ~2-5 seconds for screenshot analysis
- Both operations run synchronously but don't block on errors
- Consider async processing for high-traffic scenarios

## Cost Considerations

- GPT-4o-mini is cost-effective (~$0.15/1M input tokens, $0.60/1M output tokens)
- Typical bug analysis: ~500 input tokens, ~200 output tokens
- Image processing: ~1000 tokens for vision analysis
- Monitor OpenAI usage in production

## Security

- API key stored in environment variables (not in code)
- User authentication required for API endpoint
- Input validation on all API requests
- No sensitive data sent to OpenAI (only bug descriptions and screenshots)

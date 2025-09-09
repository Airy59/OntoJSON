# JSON Schema Validation Feature Guide

## How to Use the Validation Feature

### 1. Access the Validation Page
- Start the web app: `python -m src.owl2jsonschema_web.app`
- Navigate to: `http://localhost:5000/validate`
- You should see "Validate" in the navigation menu

### 2. Using the Validation Interface

#### Quick Test with Example Data:
1. Click the **"Load Example"** button - This loads sample schema and data
2. Click **"Validate JSON"** button
3. Results will appear below in the "Validation Results" section

#### What You Should See:

**For Valid Data:**
```
✅ Validation Successful!
All JSON data is valid according to the schema.
Validated 1 instance(s) successfully.
```

**For Invalid Data:**
```
❌ Validation Failed
[List of specific errors]
```

### 3. Testing Invalid Data

To see validation errors, try this:

1. Click "Load Example" first
2. In the JSON Data field (right side), remove the "name" field
3. Click "Validate JSON"
4. You should see:
   - Red error alert
   - Error message: "'name' is a required property"

### 4. The Validation Results Section

The results appear in a card below the input areas with:
- **Status indicator**: ✅ for valid, ❌ for invalid
- **Error details**: Specific validation errors with paths
- **Detailed Report**: A formatted report (appears when errors occur)

### 5. Two Validation Modes

The page has two tabs:
1. **Validate JSON Data** - Validates JSON against a schema
2. **Validate Schema** - Checks if a schema itself is valid Draft 7

## Troubleshooting

If you don't see results:

1. **Check Browser Console** (F12 > Console tab) for JavaScript errors
2. **Ensure both fields have content** before clicking Validate
3. **Try the Load Example button** first to ensure valid JSON format

## Manual Test Steps

1. Start the web app
2. Go to http://localhost:5000/validate
3. Click "Load Example"
4. Click "Validate JSON"
5. You should see a green success message

Then test with invalid data:
1. Delete the "name" field from the JSON data
2. Click "Validate JSON" again
3. You should see a red error message with details

## API Testing

You can also test via API:

```bash
# Test valid data
curl -X POST http://localhost:5000/api/validate/json \
  -H "Content-Type: application/json" \
  -d '{
    "schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    "data": {"name": "Test"},
    "include_report": true
  }'
```

The response will include:
- `validation.valid`: true/false
- `validation.errors`: Array of errors (if any)
- `report`: Human-readable report (if requested)
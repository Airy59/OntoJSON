# OntoJSON Web Application Guide

This guide explains how to use the new web interface for OntoJSON, which provides a browser-based alternative to the desktop GUI and CLI interfaces.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Running the Web App](#running-the-web-app)
- [Using the Web Interface](#using-the-web-interface)
- [REST API Documentation](#rest-api-documentation)
- [Configuration](#configuration)
- [Deployment](#deployment)

## Architecture Overview

OntoJSON now supports multiple interfaces through a shared service layer:

```
┌─────────────────────────────────────────────┐
│           Presentation Layer                 │
├──────────┬──────────┬──────────┬────────────┤
│   CLI    │   PyQt6  │   Flask  │   REST     │
│Interface │   GUI    │   Web UI │   API      │
└──────────┴──────────┴──────────┴────────────┘
                      │
┌─────────────────────▼─────────────────────────┐
│          Service Layer (Shared)               │
├────────────────────────────────────────────────┤
│ • TransformationService                       │
│ • ConfigurationService                        │
│ • FileService (with adapters)                 │
└────────────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────┐
│              Core Engine                      │
├────────────────────────────────────────────────┤
│ • TransformationEngine                        │
│ • OntologyParser                              │
│ • SchemaBuilder                               │
│ • Rules System                                │
└────────────────────────────────────────────────┘
```

## Installation

### Basic Installation
```bash
# Clone the repository (if not already done)
git clone https://github.com/your-repo/OntoJSON.git
cd OntoJSON

# Install core dependencies
pip install -e .
```

### Web Interface Dependencies
```bash
# Install Flask and web dependencies
pip install -e ".[web]"

# Or install individually
pip install Flask flask-cors flask-session
```

### Optional: Async Processing with Celery
```bash
# For async task processing
pip install celery redis

# Start Redis server (required for Celery)
redis-server
```

## Running the Web App

### Development Mode
```bash
# From the project root directory
cd src/owl2jsonschema_web
python app.py

# The app will be available at http://localhost:5000
```

### Production Mode
```bash
# Set environment variables
export FLASK_CONFIG=production
export SECRET_KEY=your-secret-key-here

# Run with a production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 'owl2jsonschema_web:create_app()'
```

### With Celery (for async processing)
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
celery -A owl2jsonschema_web.tasks worker --loglevel=info

# Terminal 3: Start Flask app
python src/owl2jsonschema_web/app.py
```

## Using the Web Interface

### Home Page
Navigate to `http://localhost:5000` to access the OntoJSON web interface.

### OWL to JSON Schema Transformation Workflow

1. **Upload Ontologies**
   - Drag and drop ontology files (.ttl, .rdf, .owl, etc.)
   - Or enter URLs for remote ontologies
   - Support for multiple ontology sources

2. **Configure Transformation**
   - Select a configuration profile
   - Choose language for labels/comments
   - Adjust advanced options as needed

3. **Assemble Composite Ontology**
   - Click "Assemble Composite Ontology" to merge multiple sources
   - View consistency validation results
   - Copy or download the assembled composite ontology

4. **Execute Transformation**
   - Click "Start Transformation" (enabled after assembly)
   - Monitor progress in real-time
   - View results in different formats

5. **Download Results**
   - Download JSON Schema
   - Download composite ontology
   - Download sample instances
   - Export as JSON-LD

### JSON Schema to OWL Reverse Transformation (NEW)

Navigate to the "JSON → OWL" page to perform reverse transformations.

1. **Input JSON Schema**
   - **Upload File**: Drag and drop or select a JSON Schema file (.json)
   - **Paste JSON**: Directly paste JSON Schema content into the text area

2. **Configure Transformation**
   - **Base Namespace URI**: Set the base URI for generated OWL classes and properties
     - Default: `http://example.org/ontology#`
     - Should end with `#` or `/`
   - **Language Tag**: Choose language for labels and descriptions (en, fr, de, es)
   - **Output Format**: Select output format
     - Turtle (.ttl) - Default, human-readable
     - RDF/XML (.owl) - XML-based format
     - JSON-LD (.jsonld) - JSON-based RDF format

3. **Validate (Optional)**
   - Click "Validate JSON Schema" to check for issues
   - View validation results and warnings
   - Helps identify potential transformation problems

4. **Transform**
   - Click "Transform to OWL" to start the transformation
   - View real-time progress
   - See transformation statistics:
     - Number of OWL classes generated
     - Number of object properties created
     - Number of datatype properties created
     - Number of individuals defined

5. **Download Results**
   - Download the generated OWL ontology in selected format
   - Copy to clipboard for direct use
   - Review transformation warnings if any

### Transformation Patterns

The reverse transformation maps JSON Schema constructs to OWL as follows:

| JSON Schema | OWL Equivalent | Description |
|-------------|----------------|-------------|
| `definitions` | OWL Classes | Each definition becomes a class |
| `properties` (string/number/boolean) | Datatype Properties | Primitive types map to datatype properties |
| `properties` (with `$ref`) | Object Properties | References map to object properties |
| `required` array | Cardinality Restrictions | Required properties get minCardinality 1 |
| `enum` values | Named Individuals | Enum values become OWL individuals |
| `allOf` | Class Hierarchy/Intersection | SubClass relationships or intersections |
| `oneOf` | Class Union | Union of classes |
| `not` | Class Complement | Complement of a class |

## REST API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Transform Single Ontology
```http
POST /api/transform
Content-Type: multipart/form-data

file: [ontology file]
config: {"rules": {...}}
language: "en"
```

#### Transform Multiple Ontologies
```http
POST /api/transform/multiple
Content-Type: application/json

{
  "sources": ["url1", "url2"],
  "composite_metadata": {
    "title": "Combined Ontology",
    "description": "..."
  },
  "config": {...}
}
```

#### Assemble Composite Ontology
```http
POST /api/assemble
Content-Type: application/json

{
  "sources": ["file1.ttl", "url2"],
  "metadata": {
    "title": "Composite Ontology",
    "version": "1.0.0",
    "author": "OntoJSON Web",
    "description": "Automatically generated composite ontology"
  }
}
```

#### Validate Ontology Consistency
```http
POST /api/validate-consistency
Content-Type: application/json

{
  "ontology_path": "/path/to/composite_ontology.ttl"
}
```

#### Generate A-box
```http
POST /api/generate/abox
Content-Type: application/json

{
  "schema": {...},
  "instance_count": 10,
  "seed": 42
}
```

#### List Available Rules
```http
GET /api/rules
```

#### Configuration Profiles
```http
GET /api/configurations
POST /api/configurations
GET /api/configurations/{profile_name}
PUT /api/configurations/{profile_name}
DELETE /api/configurations/{profile_name}
```

#### Reverse Transformation: JSON Schema to OWL

##### Transform JSON Schema to OWL
```http
POST /api/reverse/transform
Content-Type: application/json

{
  "schema": {...},
  "base_namespace": "http://example.org/ontology#",
  "language": "en",
  "format": "turtle"
}
```

Response:
```json
{
  "success": true,
  "ontology": "# OWL ontology in Turtle format\n...",
  "format": "turtle",
  "statistics": {
    "classes": 5,
    "object_properties": 3,
    "datatype_properties": 7,
    "individuals": 0,
    "total_triples": 45
  },
  "warnings": []
}
```

##### Validate JSON Schema
```http
POST /api/reverse/validate
Content-Type: application/json

{
  "schema": {...}
}
```

Response:
```json
{
  "valid": true,
  "error": null,
  "warnings": [
    "Missing '$schema' field - schema version is recommended"
  ],
  "schema_version": "http://json-schema.org/draft-07/schema#"
}
```

##### Preview Transformation Patterns
```http
GET /api/reverse/preview
```

Response:
```json
{
  "patterns": [
    {
      "json_schema": "definitions",
      "owl": "OWL Classes",
      "description": "Each definition becomes an OWL class",
      "example": {...}
    },
    ...
  ],
  "supported_formats": ["turtle", "xml", "json-ld"]
}
```

##### Get Available Output Formats
```http
GET /api/reverse/formats
```

Response:
```json
{
  "formats": [
    {
      "name": "turtle",
      "extension": ".ttl",
      "mime_type": "text/turtle",
      "description": "Turtle (Terse RDF Triple Language)"
    },
    ...
  ]
}
```

#### Async Tasks
```http
POST /api/tasks
GET /api/tasks/{task_id}
POST /api/tasks/{task_id}/cancel
GET /api/tasks
```

### Example: Using curl
```bash
# Transform a local file
curl -X POST -F "file=@ontology.ttl" \
  http://localhost:5000/api/transform

# Transform from URL
curl -X POST -H "Content-Type: application/json" \
  -d '{"source": "http://example.com/ontology.ttl"}' \
  http://localhost:5000/api/transform
```

## Configuration

### Application Configuration
Edit `src/owl2jsonschema_web/config.py`:

```python
class Config:
    SECRET_KEY = 'your-secret-key'
    UPLOAD_FOLDER = '/path/to/uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
    # Celery configuration
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### Environment Variables
```bash
export FLASK_CONFIG=development|production|testing
export SECRET_KEY=your-secret-key
export UPLOAD_FOLDER=/path/to/uploads
export REDIS_URL=redis://localhost:6379/0
```

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[web]"

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", \
     "owl2jsonschema_web:create_app()"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_CONFIG=production
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  worker:
    build: .
    command: celery -A owl2jsonschema_web.tasks worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

### Nginx Configuration (for production)
```nginx
server {
    listen 80;
    server_name ontojson.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/OntoJSON/src/owl2jsonschema_web/static;
        expires 30d;
    }

    client_max_body_size 100M;
}
```

## Features

### Multi-Platform Support
- **CLI**: Command-line interface for automation
- **Desktop GUI**: PyQt6-based native application
- **Web Interface**: Browser-based interface with Assembly feature
- **REST API**: Programmatic access for integration

### File Handling
- Local file uploads
- Remote URL fetching
- Multiple file processing
- Automatic composite creation with validation

### Ontology Assembly
- Create composite ontologies from multiple sources
- Consistency validation using reasoner
- Visual feedback on assembly status
- Download assembled composite ontology

### Async Processing
- Long-running transformations in background
- Real-time progress updates
- Task management and cancellation

### Configuration Management
- Predefined profiles
- Custom rule configurations
- Persistent settings

## Troubleshooting

### Common Issues

1. **Flask not found**
   ```bash
   pip install Flask flask-cors flask-session
   ```

2. **Redis connection error**
   ```bash
   # Start Redis server
   redis-server
   ```

3. **File upload size limit**
   - Adjust `MAX_CONTENT_LENGTH` in config
   - Update nginx `client_max_body_size` if using nginx

4. **CORS issues**
   - Ensure `flask-cors` is installed
   - Check CORS configuration in `__init__.py`

## API Client Examples

### Python
```python
import requests

# Transform ontology
with open('ontology.ttl', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/transform',
        files={'file': f}
    )
    
result = response.json()
print(result['schema'])
```

### JavaScript
```javascript
// Transform from URL
fetch('http://localhost:5000/api/transform', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        source: 'http://example.com/ontology.ttl'
    })
})
.then(response => response.json())
.then(data => console.log(data.schema));
```

## Security Considerations

### Production Deployment
- Always use a strong `SECRET_KEY`
- Enable HTTPS with SSL certificates
- Implement rate limiting
- Add authentication for sensitive endpoints
- Validate and sanitize all inputs
- Use a reverse proxy (nginx/Apache)
- Keep dependencies updated

### File Upload Security
- Limit file sizes
- Validate file types
- Scan for malware
- Use secure file storage
- Implement user quotas

## Support

For issues specific to the web interface:
- Check the [GitHub Issues](https://github.com/your-repo/OntoJSON/issues)
- Review the [API Documentation](#rest-api-documentation)
- Contact the development team

## License

See the main [LICENSE](LICENSE) file for details.
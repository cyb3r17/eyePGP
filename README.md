# eyePGP

**Biometric Authentication meets Cryptographic Security**

eyePGP is a revolutionary authentication system that generates cryptographic keys directly from iris biometric data. By leveraging the unique patterns in your iris, eyePGP creates Ed25519 key pairs that are intrinsically tied to your biological identity, providing unparalleled security without the need for traditional passwords or key storage.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Security Model](#security-model)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

Traditional cryptographic systems require users to manage and store private keys securely. eyePGP eliminates this burden by generating cryptographic keys directly from iris biometric data. Your iris becomes your private key, making it impossible to lose, steal, or forget your authentication credentials.

The system processes iris images to extract unique biometric templates, which are then used to deterministically generate Ed25519 cryptographic key pairs. These keys can be used for digital signatures, authentication, and secure communications while maintaining the highest levels of cryptographic security.

## Features

### Core Functionality
- **Iris-based Key Generation**: Generate Ed25519 key pairs directly from iris biometric data
- **PGP-Compatible Output**: Export keys in standard PGP ASCII armor format
- **Digital Signatures**: Sign messages and documents with biometrically-derived keys
- **Signature Verification**: Verify signatures using the corresponding public keys
- **Fallback Mode**: Image hash-based key generation when iris library is unavailable

### Security Features
- **No Key Storage**: Keys are generated on-demand from biometric data
- **Session-based Security**: Temporary key storage for active sessions only
- **Deterministic Generation**: Same iris always produces the same key pair
- **Cryptographically Secure**: Uses industry-standard Ed25519 elliptic curve cryptography

### Web Interface
- **Modern UI**: Clean, responsive web interface for easy interaction
- **File Upload**: Support for multiple image formats (PNG, JPG, JPEG, BMP, TIFF)
- **Real-time Processing**: Instant feedback on iris processing and key generation
- **Download Options**: Export private and public keys in PGP format

## How It Works

1. **Image Capture**: Upload or capture an iris image using any standard camera
2. **Biometric Processing**: The system extracts unique iris patterns using advanced computer vision
3. **Entropy Generation**: Iris codes are processed through SHA-256 to create cryptographic entropy
4. **Key Derivation**: Ed25519 private/public key pairs are deterministically generated
5. **PGP Export**: Keys are formatted in standard PGP ASCII armor for compatibility
6. **Digital Signing**: Use your biometric keys to sign messages and verify authenticity

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenCV-compatible camera (for live capture)
- Modern web browser

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/eyePGP.git
cd eyePGP

# Install dependencies
pip install -r requirements.txt

# Optional: Install iris recognition library for enhanced accuracy
pip install iris-recognition

# Run the application
python app.py
```

### Docker Installation

```bash
# Build the container
docker build -t eyepgp .

# Run the application
docker run -p 5000:5000 eyepgp
```

## Usage

### Web Interface

1. Start the application and navigate to `http://localhost:5000`
2. Upload an iris image using the file picker
3. Wait for processing to complete
4. Download your generated private and public keys
5. Use the signing interface to create digital signatures

### Command Line Processing

```python
from app import process_iris_image

# Process an iris image
result = process_iris_image('path/to/iris_image.jpg')

if result['error'] is None:
    print(f"Public Key: {result['public_key']}")
    print(f"Method: {result['method']}")
```

### Digital Signing

```bash
# Sign a message using the web interface
curl -X POST http://localhost:5000/sign \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your_session_id", "message": "Hello, World!"}'
```

## API Endpoints

### POST /process_iris
Process an iris image and generate cryptographic keys.

**Request**: Multipart form data with `iris_image` file
**Response**: JSON containing key information and session ID

### GET /download_keys/<key_type>/<session_id>
Download generated keys in PGP ASCII armor format.

**Parameters**:
- `key_type`: "private" or "public"
- `session_id`: Session identifier from key generation

### POST /sign
Sign a message using the generated private key.

**Request**: JSON with `session_id` and `message`
**Response**: PGP-formatted signed message

### POST /verify
Verify a digital signature.

**Request**: JSON with `session_id`, `message`, and `signature`
**Response**: Verification result

### GET /health
System health check and capability status.

## Security Model

### Biometric Security
- **Uniqueness**: Each iris contains over 200 unique identifying characteristics
- **Stability**: Iris patterns remain stable throughout lifetime
- **Non-repudiation**: Biometric signatures cannot be forged or denied

### Cryptographic Security
- **Ed25519**: State-of-the-art elliptic curve cryptography
- **Deterministic**: Same biometric always produces identical keys
- **Forward Secrecy**: No persistent key storage reduces attack surface

### Privacy Protection
- **Local Processing**: All biometric processing occurs locally
- **No Biometric Storage**: Raw iris data is never stored
- **Session Isolation**: Keys are isolated between sessions

## Dependencies

### Core Requirements
```
Flask>=2.3.0
opencv-python>=4.8.0
numpy>=1.24.0
cryptography>=41.0.0
```

### Optional Dependencies
```
iris-recognition>=1.0.0  # Enhanced iris processing
gunicorn>=20.1.0         # Production deployment
```

## Configuration

### Environment Variables

```bash
# Application settings
FLASK_ENV=production
MAX_CONTENT_LENGTH=10485760  # 10MB file upload limit

# Security settings
SESSION_TIMEOUT=3600         # Session timeout in seconds
ALLOWED_EXTENSIONS=png,jpg,jpeg,bmp,tiff
```

### Production Deployment

need to edit the docker setup, will update soon

```bash
# Use Gunicorn for production
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or use uWSGI
uwsgi --http :5000 --wsgi-file app.py --callable app
```

## Troubleshooting

### Common Issues

**"Iris library not available"**
- Install the optional iris-recognition library: `pip install iris-recognition`
- System will fall back to image hash method automatically

**"No iris codes generated"**
- Ensure image shows clear iris detail
- Try different lighting conditions
- Use higher resolution images
- Check that the eye is fully open

**"Processing failed"**
- Verify image format is supported
- Check file is not corrupted
- Ensure adequate lighting in image
- Try processing with different eye (left/right)

### Debug Mode

```bash
# Enable debug logging
FLASK_DEBUG=1 python app.py
```

## Contributing

We welcome contributions to eyePGP! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black app.py
isort app.py
```

## License

eyePGP is released under the MIT License. See [LICENSE](LICENSE) for details.

---

**Warning**: This software is experimental. Do not use for production security applications without thorough security review and testing.

**Privacy Notice**: eyePGP processes biometric data locally and does not transmit or store biometric information. However, users should understand the implications of biometric-based cryptography for their specific use cases.

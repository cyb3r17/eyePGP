from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np
import os
import tempfile
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
import base64
import time
from datetime import datetime
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Check if iris library is available
try:
    import iris
    IRIS_AVAILABLE = True
    print("Iris recognition library loaded successfully")
except ImportError:
    IRIS_AVAILABLE = False
    print("Warning: iris library not available. Install with: pip install iris-recognition")

def process_iris_image(image_path):
    """Process iris image and generate cryptographic keys"""
    try:
        # Load image
        img_pixels = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img_pixels is None:
            return {"error": "Could not load image file"}
        
        if not IRIS_AVAILABLE:
            # Fallback: generate keys from image hash (not secure for production)
            img_hash = sha256(img_pixels.flatten().tobytes()).digest()[:32]
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(img_hash)
            public_key = private_key.public_key()
            
            return {
                "error": None,
                "warning": "Using image hash fallback - iris library not available",
                "private_key": private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                ).hex(),
                "public_key": public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                ).hex(),
                "method": "image_hash",
                "private_key_obj": private_key,
                "public_key_obj": public_key
            }
        
        # Use iris recognition pipeline
        iris_pipeline = iris.IRISPipeline()
        output = iris_pipeline(img_data=img_pixels, eye_side="right")
        
        if output["error"] is not None:
            # Try left eye if right eye fails
            output = iris_pipeline(img_data=img_pixels, eye_side="left")
            
        if output["error"] is not None:
            return {"error": f"Iris processing failed: {output['error']}"}
        
        if not output["iris_template"].iris_codes:
            return {"error": "No iris codes generated from image"}
        
        # Generate keys from iris template
        iris_codes = output["iris_template"].iris_codes[0]
        entropy = sha256(iris_codes.flatten().tobytes()).digest()[:32]
        
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(entropy)
        public_key = private_key.public_key()
        
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "error": None,
            "private_key": priv_bytes.hex(),
            "public_key": pub_bytes.hex(),
            "iris_codes_count": len(output["iris_template"].iris_codes),
            "method": "iris_biometric",
            "private_key_obj": private_key,
            "public_key_obj": public_key
        }
        
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

def create_pgp_armor(data, header_type, comment=None):
    """Create PGP ASCII armor format"""
    armor_header = f"-----BEGIN PGP {header_type}-----"
    armor_footer = f"-----END PGP {header_type}-----"
    
    lines = [armor_header]
    if comment:
        lines.append(f"Comment: {comment}")
    lines.append("")  # Empty line after headers
    
    # Base64 encode the data and split into 64-character lines
    b64_data = base64.b64encode(data).decode('ascii')
    for i in range(0, len(b64_data), 64):
        lines.append(b64_data[i:i+64])
    
    # Add checksum (simplified - real PGP uses CRC24)
    checksum = base64.b64encode(sha256(data).digest()[:3]).decode('ascii')
    lines.append(f"={checksum}")
    lines.append(armor_footer)
    
    return '\n'.join(lines)

def ed25519_to_pgp_format(private_key, public_key, user_id="Anarchy Auth User"):
    """Convert Ed25519 keys to PGP-like format"""
    timestamp = int(time.time())
    
    # Get raw key bytes
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    # Create simplified PGP-like packet structure
    # This is a simplified format for compatibility
    private_packet = (
        b'\x04' +  # Version 4
        timestamp.to_bytes(4, 'big') +  # Creation time
        b'\x16' +  # Ed25519 algorithm ID
        private_bytes +
        public_bytes
    )
    
    public_packet = (
        b'\x04' +  # Version 4
        timestamp.to_bytes(4, 'big') +  # Creation time
        b'\x16' +  # Ed25519 algorithm ID
        public_bytes
    )
    
    return private_packet, public_packet

# Store keys temporarily (in production, use secure session management)
active_keys = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_iris', methods=['POST'])
def process_iris():
    if 'iris_image' not in request.files:
        return jsonify({"error": "No file uploaded"})
    
    file = request.files['iris_image']
    if file.filename == '':
        return jsonify({"error": "No file selected"})
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Please upload PNG, JPG, BMP, or TIFF"})
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
        file.save(temp_file.name)
        temp_path = temp_file.name
    
    try:
        # Process the iris image
        result = process_iris_image(temp_path)
        
        if result["error"] is None:
            # Store keys for later use (session-based in production)
            session_id = sha256(f"{time.time()}{result['public_key']}".encode()).hexdigest()[:16]
            active_keys[session_id] = {
                'private_key': result['private_key_obj'],
                'public_key': result['public_key_obj'],
                'created': datetime.now(),
                'method': result['method']
            }
            result['session_id'] = session_id
            
            # Remove key objects from response
            del result['private_key_obj']
            del result['public_key_obj']
        
        return jsonify(result)
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.route('/download_keys/<key_type>/<session_id>')
def download_keys(key_type, session_id):
    if session_id not in active_keys:
        return jsonify({"error": "Session expired or invalid"}), 404
    
    key_data = active_keys[session_id]
    private_key = key_data['private_key']
    public_key = key_data['public_key']
    
    try:
        if key_type == 'private':
            private_packet, _ = ed25519_to_pgp_format(private_key, public_key)
            armor_data = create_pgp_armor(
                private_packet, 
                "PRIVATE KEY BLOCK",
                f"Generated by Anarchy Auth - {key_data['method']}"
            )
            filename = f"anarchy-auth-private-{session_id[:8]}.asc"
            
        elif key_type == 'public':
            _, public_packet = ed25519_to_pgp_format(private_key, public_key)
            armor_data = create_pgp_armor(
                public_packet,
                "PUBLIC KEY BLOCK", 
                f"Generated by Anarchy Auth - {key_data['method']}"
            )
            filename = f"anarchy-auth-public-{session_id[:8]}.asc"
            
        else:
            return jsonify({"error": "Invalid key type"}), 400
            
        # Create file-like object
        file_obj = io.BytesIO(armor_data.encode('utf-8'))
        file_obj.seek(0)
        
        return send_file(
            file_obj,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pgp-keys'
        )
        
    except Exception as e:
        return jsonify({"error": f"Key generation failed: {str(e)}"}), 500

@app.route('/sign', methods=['POST'])
def sign_data():
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message', '')
    
    if session_id not in active_keys:
        return jsonify({"error": "Session expired or invalid"}), 404
    
    if not message:
        return jsonify({"error": "No message to sign"}), 400
    
    try:
        private_key = active_keys[session_id]['private_key']
        
        # Sign the message
        message_bytes = message.encode('utf-8')
        signature = private_key.sign(message_bytes)
        
        # Create PGP-style signed message
        signature_b64 = base64.b64encode(signature).decode('ascii')
        
        signed_message = f"""-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

{message}
-----BEGIN PGP SIGNATURE-----
Comment: Signed with Anarchy Auth biometric key

{signature.hex()}
-----END PGP SIGNATURE-----"""
        
        return jsonify({
            "error": None,
            "signed_message": signed_message,
            "signature": signature.hex(),
            "message_hash": sha256(message_bytes).hexdigest()
        })
        
    except Exception as e:
        return jsonify({"error": f"Signing failed: {str(e)}"}), 500

@app.route('/verify', methods=['POST'])
def verify_signature():
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message', '')
    signature_hex = data.get('signature', '')
    
    if session_id not in active_keys:
        return jsonify({"error": "Session expired or invalid"}), 404
    
    if not message or not signature_hex:
        return jsonify({"error": "Message and signature required"}), 400
    
    try:
        public_key = active_keys[session_id]['public_key']
        
        # Convert hex signature back to bytes
        signature = bytes.fromhex(signature_hex)
        message_bytes = message.encode('utf-8')
        
        # Verify signature
        try:
            public_key.verify(signature, message_bytes)
            return jsonify({
                "error": None,
                "valid": True,
                "message": "Signature is valid"
            })
        except Exception:
            return jsonify({
                "error": None,
                "valid": False,
                "message": "Signature is invalid"
            })
            
    except Exception as e:
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "iris_library": IRIS_AVAILABLE,
        "opencv": True,
        "cryptography": True,
        "active_sessions": len(active_keys)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
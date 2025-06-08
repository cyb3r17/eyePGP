from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import os
import tempfile
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

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

def plot_to_base64(figure):
    """Convert matplotlib figure to base64 string"""
    buffer = io.BytesIO()
    figure.savefig(buffer, format='png', bbox_inches='tight', 
                   facecolor='black', edgecolor='none', dpi=100)
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close(figure)
    
    graphic = base64.b64encode(image_png)
    return graphic.decode('utf-8')

def generate_visualizations(img_pixels, iris_pipeline, output):
    """Generate visualization images from iris processing"""
    visualizations = {}
    
    if not IRIS_AVAILABLE:
        return visualizations
    
    try:
        iris_visualizer = iris.visualisation.IRISVisualizer()
        
        # 1. Original IR Image visualization
        try:
            fig = plt.figure(figsize=(8, 6))
            fig.patch.set_facecolor('black')
            canvas = iris_visualizer.plot_ir_image(iris.IRImage(img_data=img_pixels, eye_side="right"))
            plt.title("Original IR Image", color='white')
            visualizations['original_image'] = plot_to_base64(fig)
        except Exception as e:
            print(f"Error generating original image plot: {e}")
        
        # 2. Iris Template visualization
        try:
            if output and output.get("iris_template"):
                fig = plt.figure(figsize=(10, 6))
                fig.patch.set_facecolor('black')
                canvas = iris_visualizer.plot_iris_template(output["iris_template"])
                plt.title("Iris Template", color='white')
                visualizations['iris_template'] = plot_to_base64(fig)
        except Exception as e:
            print(f"Error generating iris template plot: {e}")
        
        # 3. Segmentation Map visualization
        try:
            if iris_pipeline and hasattr(iris_pipeline, 'call_trace') and 'segmentation' in iris_pipeline.call_trace:
                fig = plt.figure(figsize=(8, 6))
                fig.patch.set_facecolor('black')
                canvas = iris_visualizer.plot_segmentation_map(
                    ir_image=iris.IRImage(img_data=img_pixels, eye_side="right"),
                    segmap=iris_pipeline.call_trace['segmentation'],
                )
                plt.title("Segmentation Map", color='white')
                visualizations['segmentation_map'] = plot_to_base64(fig)
        except Exception as e:
            print(f"Error generating segmentation plot: {e}")
        
        # 4. Pipeline parameters info
        try:
            if iris_pipeline and hasattr(iris_pipeline, 'params'):
                pipeline_info = str(iris_pipeline.params.pipeline)
                visualizations['pipeline_info'] = pipeline_info
        except Exception as e:
            print(f"Error getting pipeline info: {e}")
            
    except Exception as e:
        print(f"General error in visualization generation: {e}")
    
    return visualizations

def process_iris_image(image_path):
    """Process iris image and generate cryptographic keys with visualizations"""
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
                "visualizations": {}
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
        
        # Generate visualizations
        visualizations = generate_visualizations(img_pixels, iris_pipeline, output)
        
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
            "visualizations": visualizations
        }
        
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

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
        return jsonify(result)
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "iris_library": IRIS_AVAILABLE,
        "opencv": True,  # We know it's available since we imported it
        "cryptography": True,  # We know it's available since we imported it
        "matplotlib": True
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
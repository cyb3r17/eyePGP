# Download and process iris image
import subprocess
import cv2
import numpy as np
import matplotlib.pyplot as plt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from hashlib import sha256

# Download image
subprocess.run(['wget', 'https://wld-ml-ai-data-public.s3.amazonaws.com/public-iris-images/example_orb_image_1.png', '-O', 'sample_ir_image.png'])

# Load and display image
img_pixels = cv2.imread("sample_ir_image.png", cv2.IMREAD_GRAYSCALE)


# Process with iris pipeline (assuming iris library is available)
try:
    import iris
    iris_pipeline = iris.IRISPipeline()
    output = iris_pipeline(img_data=img_pixels, eye_side="right")

    if output["error"] is None:
        print(f"Success! Generated {len(output['iris_template'].iris_codes)} iris codes")

        # Visualize results
        iris_visualizer = iris.visualisation.IRISVisualizer()
        canvas = iris_visualizer.plot_iris_template(output["iris_template"])
        plt.show()

        # Generate cryptographic keys from iris template
        iris_codes = output["iris_template"].iris_codes[0]  # Use first iris code
        entropy = sha256(iris_codes.flatten().tobytes()).digest()[:32]

        # Create keys
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

        print(f"Private Key ({len(priv_bytes)} bytes): {priv_bytes.hex().zfill(64)}")
        print(f"Public Key ({len(pub_bytes)} bytes): {pub_bytes.hex().zfill(64)}")

except ImportError:
    print("iris library not available - install with: pip install iris-recognition")
except Exception as e:
    print(f"Error processing iris: {e}")
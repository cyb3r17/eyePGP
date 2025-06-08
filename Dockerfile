FROM python:3.10-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    flask \
    opencv-python \
    numpy \
    matplotlib \
    cryptography \
    open-iris

COPY . .

CMD ["python", "server.py"]

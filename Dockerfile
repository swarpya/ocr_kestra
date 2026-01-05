FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Install CPU Torch stack FIRST
RUN pip install --no-cache-dir \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# 3. Install Surya WITHOUT dependencies
RUN pip install --no-cache-dir --no-deps surya-ocr

# 4. Manually install dependencies + FastAPI Server tools
# ADDED: fastapi, uvicorn, python-multipart
RUN pip install --no-cache-dir \
    transformers \
    pillow \
    pypdfium2 \
    pytesseract \
    opencv-python-headless \
    filetype \
    click \
    numpy \
    huggingface-hub \
    safetensors \
    pyyaml \
    tqdm \
    pydantic \
    pydantic-settings \
    python-dotenv \
    platformdirs \
    scipy \
    fastapi \
    uvicorn \
    python-multipart

WORKDIR /app

# Copy the API code into the container
COPY api_server.py /app/api_server.py

# Start the API server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
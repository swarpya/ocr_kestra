FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 1. System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    git \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 2. Torch (CPU)
RUN pip install --no-cache-dir \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# 3. OCR Engines
RUN pip install --no-cache-dir --no-deps surya-ocr

# 4. Server Dependencies (Added pandas, openpyxl, python-pptx)
RUN pip install --no-cache-dir \
    transformers \
    pillow \
    pypdfium2 \
    pytesseract \
    opencv-python-headless \
    filetype \
    click \
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
    python-multipart \
    requests \
    numpy \
    pandas \
    openpyxl \
    python-pptx

WORKDIR /app
COPY api_server.py /app/api_server.py

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
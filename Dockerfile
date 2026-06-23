# Modify line 1: Switch to a PyTorch CUDA runtime image
FROM docker.io/pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

WORKDIR /src

# Install libsndfile1 for the soundfile Python package
RUN apt-get update && apt-get install -y libsndfile1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
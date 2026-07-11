# Modify line 1: Switch to a PyTorch CUDA runtime image
FROM nvcr.io/nvidia/pytorch:26.06-py3

WORKDIR /src

# Install libsndfile1 for the soundfile Python package
RUN apt-get update && apt-get install -y libsndfile1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
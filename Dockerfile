# Modify line 1: Switch to a PyTorch CUDA runtime image
from pytorch/pytorch:2.13.0-cuda13.2-cudnn9-runtime


COPY requirements.txt .
RUN pip install -r requirements.txt --break-system-packages

# Install libsndfile1 for the soundfile Python package
RUN apt-get update && apt-get install -y libsndfile1 bash  && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["bash",  "init.sh"]
FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y build-essential cmake \
    libopenblas-dev liblapack-dev libx11-dev \
    libgtk-3-dev libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    pip install --upgrade pip

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "api.app:app"]

# Use official Python 3.8 slim image as the base
FROM python:3.8-slim

# Install system dependencies needed for dlib, opencv, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in container
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose port 8000 (or your Flask port)
EXPOSE 8000

# Start the app with gunicorn (adjust path if needed)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "api.app:app"]

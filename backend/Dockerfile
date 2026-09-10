# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# OpenCV headless is used, so no system UI dependencies are needed

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies (installing torch CPU explicitly to save massive amounts of space)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose the port
EXPOSE 8000

# Run the FastAPI server using Uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

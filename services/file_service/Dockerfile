# Use Python base image
FROM python:3.13.1

# Set working directory
WORKDIR /app

COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the Flask port
EXPOSE 80

# Run the service
CMD ["python", "file.py"]

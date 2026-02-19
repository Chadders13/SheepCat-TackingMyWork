FROM python:3.11-slim

# Install tkinter dependencies for GUI support
RUN apt-get update && apt-get install -y \
    python3-tk \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ /app/src/

# Create directory for logs (volume mount point)
VOLUME /app/logs

# Set display environment variable for GUI
ENV DISPLAY=:0

# Run the application
CMD ["python", "src/MyWorkTracker.py"]

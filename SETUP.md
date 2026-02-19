# SheepCat - Setup Instructions

This guide will walk you through setting up and running SheepCat, a neurodivergent-friendly task tracking application.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Python Setup](#python-setup)
- [LLM Configuration (Ollama)](#llm-configuration-ollama)
- [Running the Application](#running-the-application)
- [Docker Setup (Optional)](#docker-setup-optional)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.7+** - [Download Python](https://www.python.org/downloads/)
- **Ollama** - Local LLM runtime for AI-powered summaries
- **Git** (optional) - For cloning the repository

## Python Setup

### 1. Clone or Download the Repository

```bash
git clone https://github.com/Chadders13/SheepCat-TackingMyWork.git
cd SheepCat-TackingMyWork
```

Or download and extract the ZIP file from GitHub.

### 2. Install Python Dependencies

The application requires the following Python packages:

- `tkinter` - GUI framework (usually comes pre-installed with Python)
- `requests` - For HTTP requests to Ollama

#### On Windows:

```bash
# tkinter usually comes with Python installation
# Install requests
pip install requests
```

#### On macOS:

```bash
# If tkinter is not available, install it via:
brew install python-tk

# Install requests
pip3 install requests
```

#### On Linux (Ubuntu/Debian):

```bash
# Install tkinter
sudo apt-get update
sudo apt-get install python3-tk

# Install requests
pip3 install requests
```

### 3. Verify Python Installation

```bash
python --version
# or
python3 --version
```

You should see Python 3.7 or higher.

## LLM Configuration (Ollama)

SheepCat uses Ollama to generate AI-powered summaries of your work activities. Follow these steps to set up Ollama:

### 1. Install Ollama

Visit [https://ollama.ai](https://ollama.ai) and download Ollama for your operating system:

- **Windows**: Download the installer and follow the setup wizard
- **macOS**: `brew install ollama` or download from the website
- **Linux**: 
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ```

### 2. Start the Ollama Service

#### On Windows/macOS:
- Ollama should start automatically after installation
- You can verify it's running by checking the system tray (Windows) or menu bar (macOS)

#### On Linux:
```bash
# Start Ollama service
ollama serve
```

The service will run on `http://localhost:11434` by default.

### 3. Download an LLM Model

The application is configured to use `deepseek-r1:8b` by default, but you can use any Ollama-compatible model:

```bash
# Download the default model (DeepSeek R1 8B - recommended for balance of speed and quality)
ollama pull deepseek-r1:8b

# Or try alternative models:
ollama pull llama2           # Meta's Llama 2 (lighter, faster)
ollama pull mistral          # Mistral 7B (good balance)
ollama pull codellama        # Optimized for code-related tasks
ollama pull deepseek-coder   # Alternative DeepSeek model
```

**Model Recommendations:**
- **Low-end hardware** (8GB RAM): `llama2` or `mistral`
- **Mid-range hardware** (16GB RAM): `deepseek-r1:8b` (default)
- **High-end hardware** (32GB+ RAM): `deepseek-r1:32b` or larger models

### 4. Verify Ollama is Running

```bash
# Test if Ollama is accessible
curl http://localhost:11434/api/tags

# Or test with a simple prompt
ollama run deepseek-r1:8b "Hello, how are you?"
```

### 5. Configure the Model in SheepCat (Optional)

If you want to use a different model, edit `src/MyWorkTracker.py`:

```python
# Line 14 in src/MyWorkTracker.py
OLLAMA_MODEL = "deepseek-r1:8b"  # Change this to your preferred model
```

For example:
```python
OLLAMA_MODEL = "llama2"  # Use Llama 2 instead
OLLAMA_MODEL = "mistral"  # Use Mistral instead
```

## Running the Application

### Start SheepCat

#### On Windows:
```bash
python src\MyWorkTracker.py
```

#### On macOS/Linux:
```bash
python3 src/MyWorkTracker.py
```

### Using the Application

1. **Start Your Day**
   - Click the "Start Day" button
   - The application will prompt you for your first task

2. **Add Tasks**
   - Enter a task description when prompted
   - Add ticket/reference IDs (comma-separated for multiple)
   - Mark if the task is resolved

3. **Hourly Check-ins**
   - The app will prompt you every hour for a new task
   - It generates summaries of your hourly work
   - A countdown timer shows time until next check-in

4. **End Your Day**
   - Click "Stop / End Day" to finish tracking
   - The app generates a final summary

5. **View Your Work Log**
   - All tasks are saved to `work_log.csv` in the application directory
   - Each entry includes:
     - Timestamp
     - Task title and ticket IDs
     - Duration
     - AI-generated summary
     - Resolution status

## Docker Setup (Optional)

While the application is designed to run natively with Python, you can containerize it if needed.

### Creating a Dockerfile

Create a `Dockerfile` in the repository root:

```dockerfile
FROM python:3.11-slim

# Install tkinter dependencies
RUN apt-get update && apt-get install -y \
    python3-tk \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install requests

# Copy application files
COPY src/ /app/src/

# Create directory for logs
RUN mkdir -p /app/logs

# Set display for GUI
ENV DISPLAY=:0

# Run the application
CMD ["python", "src/MyWorkTracker.py"]
```

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t sheepcat-tracker .

# Run the container (requires X11 forwarding for GUI)
# On Linux:
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/work_log.csv:/app/work_log.csv \
  --network host \
  sheepcat-tracker

# On Windows with VcXsrv:
# 1. Install VcXsrv
# 2. Start XLaunch with "Disable access control"
docker run -it --rm \
  -e DISPLAY=host.docker.internal:0 \
  -v %cd%/work_log.csv:/app/work_log.csv \
  --network host \
  sheepcat-tracker

# On macOS with XQuartz:
# 1. Install XQuartz
# 2. Run: xhost + localhost
docker run -it --rm \
  -e DISPLAY=docker.for.mac.host.internal:0 \
  -v $(pwd)/work_log.csv:/app/work_log.csv \
  --network host \
  sheepcat-tracker
```

### Docker Compose Setup

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  sheepcat:
    build: .
    environment:
      - DISPLAY=${DISPLAY}
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - ./work_log.csv:/app/work_log.csv
    network_mode: host
    stdin_open: true
    tty: true
```

Run with:
```bash
docker-compose up
```

**Important Notes for Docker:**
- The application requires a GUI, so you need X11 forwarding configured
- Ollama must be running on the host machine (not in the container)
- The `--network host` flag allows the container to access Ollama on `localhost:11434`
- Work logs are mounted as a volume to persist data

## Troubleshooting

### Ollama Connection Issues

**Error:** `LLM Connection Failed: Connection refused`

**Solution:**
1. Verify Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Check if the Ollama service started:
   - Windows/macOS: Look for Ollama in system tray/menu bar
   - Linux: Run `ollama serve` in a terminal

3. Ensure the correct URL and port in `src/MyWorkTracker.py`:
   ```python
   OLLAMA_URL = "http://localhost:11434/api/generate"
   ```

### Model Not Found

**Error:** `Error: 404` when generating summaries

**Solution:**
```bash
# List available models
ollama list

# Download the required model
ollama pull deepseek-r1:8b
```

### tkinter Not Found

**Error:** `ModuleNotFoundError: No module named 'tkinter'`

**Solution:**
- **Windows**: Reinstall Python with tkinter enabled
- **macOS**: `brew install python-tk`
- **Linux**: `sudo apt-get install python3-tk`

### Permission Issues with CSV File

**Error:** Cannot write to `work_log.csv`

**Solution:**
```bash
# Ensure the application directory is writable
chmod +w /path/to/SheepCat-TackingMyWork
```

### Docker GUI Issues

**Error:** Cannot connect to display

**Solution:**
- **Linux**: Run `xhost +local:docker` before starting the container
- **Windows**: Ensure VcXsrv is running and "Disable access control" is checked
- **macOS**: Ensure XQuartz is running and `xhost + localhost` has been executed

## Advanced Configuration

### Customizing Check-in Intervals

By default, the application checks in every hour. To modify this, edit line 174 in `src/MyWorkTracker.py`:

```python
# Change 3600000 (1 hour in milliseconds) to your preferred interval
# Examples:
self.timer_id = self.root.after(1800000, self.hourly_checkin)  # 30 minutes
self.timer_id = self.root.after(5400000, self.hourly_checkin)  # 90 minutes
```

### Changing the Ollama URL

If Ollama is running on a different machine or port, update line 12:

```python
OLLAMA_URL = "http://your-server:11434/api/generate"
```

### Modifying the Log File Location

To change where work logs are saved, update line 15:

```python
LOG_FILE = "/path/to/your/work_log.csv"
```

## System Requirements

### Minimum Requirements:
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.7 or higher
- **RAM**: 4GB (8GB recommended for LLM operations)
- **Storage**: 50MB for application + 2-10GB for LLM models

### Recommended Requirements:
- **OS**: Windows 11, macOS 12+, or Ubuntu 22.04+
- **Python**: 3.10 or higher
- **RAM**: 16GB
- **Storage**: 20GB for multiple LLM models

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/Chadders13/SheepCat-TackingMyWork/issues)
2. Create a new issue with:
   - Your operating system
   - Python version (`python --version`)
   - Ollama version (`ollama --version`)
   - Error messages or screenshots
   - Steps to reproduce the problem

## Privacy and Data

- All data stays on your local machine
- Work logs are stored in `work_log.csv` (plain text, can be opened in Excel/Numbers)
- No data is sent to external servers (Ollama runs locally)
- You can back up your work logs by copying the CSV file

---

*Made with 💙 for the neurodivergent community*

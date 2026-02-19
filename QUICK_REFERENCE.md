# Quick Reference Guide

## Starting the Application

### Using Python (Recommended)
```bash
python src/MyWorkTracker.py
# or on macOS/Linux
python3 src/MyWorkTracker.py
```

### Using Docker
```bash
# First time setup
docker-compose up --build

# Subsequent runs
docker-compose up
```

## Common Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install and Setup Ollama
```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Download the model
ollama pull deepseek-r1:8b
```

### Verify Ollama is Running
```bash
curl http://localhost:11434/api/tags
```

## Application Workflow

1. **Start Day** → Click "Start Day" button
2. **Enter First Task** → Describe what you're working on
3. **Work** → App tracks in background
4. **Hourly Check-in** → App prompts you after each hour
5. **End Day** → Click "Stop / End Day" button

## File Locations

- **Application**: `src/MyWorkTracker.py`
- **Work Log**: `work_log.csv` (created automatically)
- **Configuration**: Edit lines 12-15 in `src/MyWorkTracker.py`

## Configuration Options

### Change LLM Model
Edit `src/MyWorkTracker.py` line 14:
```python
OLLAMA_MODEL = "deepseek-r1:8b"  # Change to your preferred model
```

### Change Check-in Interval
Edit `src/MyWorkTracker.py` line 174:
```python
self.timer_id = self.root.after(3600000, self.hourly_checkin)  # 3600000 = 1 hour in ms
```

### Change Ollama URL
Edit `src/MyWorkTracker.py` line 12:
```python
OLLAMA_URL = "http://localhost:11434/api/generate"  # Change if Ollama is on different host
```

## Recommended LLM Models

| Model | RAM Required | Best For |
|-------|-------------|----------|
| `llama2` | 8GB | Low-end hardware, faster responses |
| `mistral` | 8GB | Balanced performance |
| `deepseek-r1:8b` | 16GB | Default, good balance (recommended) |
| `deepseek-coder` | 16GB | Code-focused tasks |
| `deepseek-r1:32b` | 32GB+ | High-quality responses |

## Troubleshooting Quick Fixes

### Ollama Not Connecting
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
# Windows/macOS: Close and reopen from system tray/menu bar
# Linux: killall ollama && ollama serve
```

### Model Not Found
```bash
# List installed models
ollama list

# Install missing model
ollama pull deepseek-r1:8b
```

### tkinter Not Found (Linux)
```bash
sudo apt-get install python3-tk
```

### Permission Denied on work_log.csv
```bash
chmod 666 work_log.csv
```

## Data Format

The `work_log.csv` file contains:
- Start Time
- End Time
- Duration (minutes)
- Ticket ID(s)
- Task Title
- System Info
- AI Summary
- Resolved Status

Open with Excel, Google Sheets, or any text editor.

## Need More Help?

See [SETUP.md](SETUP.md) for detailed instructions or visit:
https://github.com/Chadders13/SheepCat-TackingMyWork/issues

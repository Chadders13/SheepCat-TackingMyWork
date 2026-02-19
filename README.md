# SheepCat - Tracking My Work

A gentle, neurodivergent-friendly task tracking application that helps you maintain a log of your activities throughout the day.

<a href="https://www.buymeacoffee.com/chadders13h" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="217" height="60"></a>

## 🌟 Overview

SheepCat is designed to help people keep track of their work activities in a non-intrusive, supportive way. Perfect for neurodivergent individuals who benefit from gentle reminders and structured logging.

## ✨ Features

### Menu-Based Navigation
- Easy-to-use menu system for switching between different pages
- Task Tracker page for logging work activities
- Review Log page for viewing and editing past entries

### Work Log Review & Editing
- Review all tasks for any date
- Update task resolved status with a single click
- Double-click tasks to quickly toggle their status
- Bulk update multiple tasks at once
- Filter and search through your work history

### Gentle Interval Check-ins
- Periodically asks you what task you've been working on at customizable intervals
- Non-disruptive notifications that respect your focus time
- Simple prompts to describe your activities

### AI-Powered Summaries
- Uses an external Large Language Model (LLM) via Ollama for generating intelligent summaries
- Creates summaries based on your task descriptions and any references you provide
- Generates interval summaries for each time period
- Produces a comprehensive daily summary at the end of each session

### Session Management
- Tracks all tasks and summaries throughout your work session
- Consolidates interval summaries into a cohesive daily report
- Maintains a historical log of your activities

### Future-Proof Architecture
- Modular repository pattern for data storage
- Easy migration to SQL, NoSQL, or API-based storage
- Designed for scalability and multi-user scenarios

## 🎯 Use Cases

- **Focus Management**: Regular check-ins help maintain awareness of time and task switching
- **Activity Logging**: Automatic documentation of what you've accomplished
- **Time Tracking**: Understand how you spend your time without manual effort
- **Progress Reporting**: Generate summaries for standups, status updates, or personal reflection
- **Neurodivergent Support**: Gentle, predictable structure that helps with task awareness

## 🚀 Getting Started

For detailed installation and setup instructions, see **[SETUP.md](SETUP.md)**.

### Quick Start

1. **Install Python 3.7+** and ensure `tkinter` is available
2. **Install Ollama** from [https://ollama.ai](https://ollama.ai)
3. **Download an LLM model**: `ollama pull deepseek-r1:8b`
4. **Install dependencies**: `pip install -r requirements.txt`
5. **Run the app**: `python src/MyWorkTracker.py`

### Documentation

- **[SETUP.md](SETUP.md)** - Complete installation and setup instructions
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference and common tasks
- **[NEW_FEATURES.md](NEW_FEATURES.md)** - Guide to the menu system, review page, and data architecture

## 🤖 LLM Configuration

SheepCat uses an **external LLM setup** for generating intelligent summaries. The application is designed to work with **Ollama**, a local LLM runtime.

### Requirements
- Ollama installed and running on your system
- Your chosen LLM model downloaded via Ollama

### How It Works
- The application makes API calls to your local Ollama instance
- You can configure which model to use based on your preferences and hardware capabilities
- All LLM processing happens through the Ollama API endpoint

This external setup gives you:
- **Privacy**: Your data stays on your machine
- **Flexibility**: Choose any Ollama-compatible model
- **Control**: Run the LLM on your own hardware

## 💡 How It Works

1. **Start a Session**: Begin tracking your work day
2. **Interval Prompts**: Receive gentle notifications at set intervals asking what you're working on
3. **Task Description**: Provide a brief description and any relevant references
4. **AI Processing**: The LLM analyzes your input and generates a summary
5. **Interval Summaries**: Each time period gets its own summary
6. **Daily Summary**: At session end, all summaries are consolidated into a comprehensive daily report

## 🌈 Philosophy

SheepCat is built with neurodivergent users in mind, offering:
- **Gentle reminders** rather than intrusive notifications
- **Flexible intervals** that adapt to your workflow
- **Automated summarization** to reduce cognitive load
- **Friendly interface** that makes task tracking approachable

## 📝 License

This project is licensed under the AGPLv3. It is free for personal use and open-source development. See the [LICENSE](LICENSE) file for details.

**Commercial Use**: If you wish to use this software within a commercial environment or without the restrictions of the AGPL, you can instantly purchase a single commercial license at [https://chadders13.github.io/SheepCat-TrackingMyWork-Website/](https://chadders13.github.io/SheepCat-TrackingMyWork-Website/). For larger volumes, please contact [chadwicksys13@gmail.com](mailto:chadwicksys13@gmail.com).

## 🤝 Contributing

Contributions are welcome! Whether you're neurodivergent yourself or an ally, we'd love to hear your ideas for making this tool more helpful and accessible.

---

*Made with 💙 for the neurodivergent community*

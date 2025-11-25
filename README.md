# FastRep

A powerful CLI and web-based tool for tracking daily work activities and generating professional reports.

[![PyPI version](https://badge.fury.io/py/fastrep.svg)](https://badge.fury.io/py/fastrep)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Easy Logging**: Quickly log your daily work activities via CLI or Web Dashboard.
- **Automatic Reports**: Generate weekly, bi-weekly, and monthly reports instantly.
- **Dual Interface**: Use either the command-line interface or the professional web UI.
- **AI Summarization**: Intelligent summarization for monthly reports using **Cline**, **OpenAI**, **Anthropic**, or **Gemini**.
- **Customizable Templates**: Choose from 7+ visual styles (Classic, Bold, Modern, Professional, etc.) with live preview.
- **App Mode**: Launches as a standalone application window for a cleaner experience.
- **Data Management**: All data stored locally in a lightweight SQLite database.
- **Theme Support**: Toggle between Light, Dark, and System themes.

## Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/hissain/fastrep/master/figures/Screenshot1.png" alt="FastRep Dashboard" width="45%">
  &nbsp; &nbsp;
  <img src="https://raw.githubusercontent.com/hissain/fastrep/master/figures/Screenshot2.png" alt="FastRep Reports" width="45%">
</p>

## Installation

```bash
pip install fastrep
```

Or install from source for development:

```bash
pip install git+https://github.com/hissain/fastrep.git
```

## Quick Start

### Web Interface

Launch the web UI:

```bash
fastrep-ui
```

The web interface will automatically open in your default browser at `http://127.0.0.1:5000`.

**Options:**
*   `--port PORT`: Run on a custom port (default: 5000).
*   `--no-browser`: Do not open the browser automatically.
*   `--verbose` / `-v`: Enable verbose logging for debugging.

### Command Line Interface

```bash
# Add a work log entry
fastrep log -p "Project Alpha" -d "Implemented user authentication"

# View weekly report
fastrep view --mode weekly
```

For a full list of commands, run `fastrep --help`.

## AI Configuration

FastRep supports AI-powered summarization for monthly reports. You can configure this in the **Settings** page of the web UI.

*   **Providers:** Supports OpenAI, Anthropic (Claude), Google Gemini, and Custom OpenAI-compatible endpoints (e.g., Ollama).
*   **Fallback:** If no API key is provided, FastRep can use the `cline` CLI if installed on your system.
*   **Customization:** You can provide custom instructions to the AI (e.g., "Use active voice") and select from various report templates.

## Project Structure

```
fastrep/
├── fastrep/
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── database.py         # Database operations
│   ├── llm.py              # AI Provider clients
│   ├── models.py           # Data models
│   ├── report_generator.py # Report generation logic
│   └── ui/
│       ├── app.py          # Flask application
│       ├── templates/      # HTML templates
│       └── static/         # CSS files
├── tests/
├── setup.py
└── README.md
```

## Contributing 

Contributions are welcome! Please feel free to submit a Pull Request.

## License 

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author 

**Md. Sazzad Hissain Khan**

- GitHub: [@hissain](https://github.com/hissain)
- Email: hissain.khan@gmail.com

## Acknowledgments 

- Built with [Click](https://click.palletsprojects.com/) for CLI
- Web UI powered by [Flask](https://flask.palletsprojects.com/)
- Database management with SQLite

## Support 

If you encounter any issues or have questions:

- Open an issue on [GitHub](https://github.com/hissain/fastrep/issues)
- Check existing issues for solutions

---

**Star ⭐ this repository if you find it helpful!**

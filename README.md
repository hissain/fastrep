# FastRep 📊

A powerful CLI and web-based tool for tracking daily work activities and generating professional reports.

[![PyPI version](https://badge.fury.io/py/fastrep.svg)](https://badge.fury.io/py/fastrep)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features ✨

- **Easy Logging**: Quickly log your daily work activities with project names and descriptions
- **Automatic Reports**: Generate weekly, bi-weekly, and monthly reports instantly
- **Dual Interface**: Use either the command-line interface or the professional web UI
- **SQLite Database**: All data stored locally in a lightweight SQLite database
- **Project Tracking**: Automatically organize logs by project
- **Flexible Dating**: Log entries for any date, not just today
- **Easy Search**: View and filter logs by date range
- **Data Management**: Delete individual entries or clear entire database
- **Dark/Light Theme**: Choose your preferred theme or sync with system settings
- **App Mode**: Launches as a standalone application window for a cleaner experience

## Screenshots 📸

<p align="center">
  <img src="https://raw.githubusercontent.com/hissain/fastrep/master/figures/Screenshot1.png" alt="FastRep Dashboard" width="45%">
  &nbsp; &nbsp;
  <img src="https://raw.githubusercontent.com/hissain/fastrep/master/figures/Screenshot2.png" alt="FastRep Reports" width="45%">
</p>

## Installation

### From PyPI (Recommended)

```bash
pip install fastrep
```

### From Source

```bash
git clone https://github.com/hissain/fastrep.git
cd fastrep
pip install -e .
```

## Quick Start

### Command Line Interface

```bash
# Add a work log entry
fastrep log -p "Project Alpha" -d "Implemented user authentication"

# Add a log for a specific date
fastrep log -p "Project Beta" -d "Fixed bug #123" --date 2024-11-15

# View weekly report
fastrep view --mode weekly

# View bi-weekly report
fastrep view --mode biweekly

# View monthly report
fastrep view --mode monthly

# List all entries
fastrep list

# View all projects
fastrep projects

# Delete a specific entry
fastrep delete --id 5

# Clear all data (with confirmation)
fastrep clear
```

### Web Interface

Launch the web UI:

```bash
fastrep-ui
```

The web interface will automatically open in your default browser at `http://127.0.0.1:5000`.

You can also specify a custom port:

```bash
fastrep-ui --port 8080
# or
fastrep-ui -p 8080
```

## Usage Examples

### Daily Workflow

```bash
# Morning: Log yesterday's work
fastrep log -p "API Development" -d "Completed endpoint for user profiles" --date 2024-11-20

# End of day: Log today's work
fastrep log -p "API Development" -d "Started work on authentication middleware"
fastrep log -p "Documentation" -d "Updated API documentation"

# Friday: Generate weekly report
fastrep view --mode weekly
```

### Report Output Example

```
Report Period: 11/16 - 11/22
============================================================

Project: API Development
------------------------------------------------------------
  * 11/21 - Started work on authentication middleware
  * 11/20 - Completed endpoint for user profiles
  * 11/18 - Fixed performance issues in database queries

Project: Documentation
------------------------------------------------------------
  * 11/21 - Updated API documentation
  * 11/19 - Created user guide for new features
```

## CLI Commands Reference

### `fastrep log`

Add a new work log entry.

**Options:**

- `-p, --project TEXT`: Project name (optional, defaults to "Misc")
- `-d, --description TEXT`: Work description (required)
- `-dt, --date TEXT`: Date in YYYY-MM-DD format (optional, defaults to today)

### `fastrep view`

View logs and generate reports.

**Options:**

- `-m, --mode [weekly|biweekly|monthly]`: Report period (default: weekly)
- `-s, --start TEXT`: Custom start date (YYYY-MM-DD)
- `-e, --end TEXT`: Custom end date (YYYY-MM-DD)

### `fastrep list`

List all log entries with their IDs.

### `fastrep projects`

List all unique projects.

### `fastrep delete`

Delete a specific log entry.

**Options:**

- `-i, --id INTEGER`: Log entry ID to delete (required)
- `-y, --confirm`: Skip confirmation prompt

### `fastrep clear`

Clear all log entries from the database.

**Options:**

- `-y, --confirm`: Skip confirmation prompt

## Web UI Features

The web interface provides:

1. **Dashboard**: Add new logs with autocomplete for project names
2. **Recent Logs Table**: View, edit, and delete entries
3. **Report Generation**: One-click weekly, bi-weekly, and monthly reports
4. **Copy to Clipboard**: Easy report copying for emails/documents
5. **Theme Support**: Toggle between Light, Dark, and System themes
6. **Settings**: Database management and configuration
7. **App Mode**: Opens in a dedicated window without browser clutter
8. **Compact Design**: Optimized form layout for quick entry

## Database Location

Logs are stored in: `~/.fastrep/fastrep.db`

Both CLI and web UI use the same database, so your data is always in sync.

## Development

### Setup Development Environment

```bash
git clone https://github.com/hissain/fastrep.git
cd fastrep
pip install -e .
```

### Project Structure

```
fastrep/
├── fastrep/
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── database.py         # Database operations
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

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

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

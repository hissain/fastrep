from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os
import shutil
import webbrowser
import click
import logging
import signal
import atexit
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Timer
from .database import Database
from .models import LogEntry
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

def setup_logging(verbosity=0):
    """Configure logging with rotating file handler."""
    log_dir = Path.home() / '.fastrep' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'fastrep.log'
    
    # Set level based on verbosity
    if verbosity >= 2:
        level = logging.DEBUG # Trace/Full content
    elif verbosity == 1:
        level = logging.INFO # Verbose steps
    else:
        level = logging.WARNING # Minimal
        
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File Handler (Rotating)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress werkzeug logs unless very verbose
    if verbosity < 2:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)


def create_app(verbosity=0):
    """Create and configure Flask application."""
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'ui', 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'ui', 'static'))
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['VERBOSITY'] = verbosity
    
    db = Database()
    
    @app.route('/')
    def index():
        """Main page with log entry form and recent logs."""
        logs = db.get_logs()
        
        # Respect recent logs limit setting
        try:
            limit_val = db.get_setting('recent_logs_limit', '20')
            limit = int(limit_val) if limit_val else 20
        except ValueError:
            limit = 20
            
        recent_logs = logs[:limit]
        total_logs = len(logs)
        
        projects = db.get_all_projects()
        today = datetime.now().strftime('%Y-%m-%d')
        return render_template('index.html', logs=recent_logs, total_logs=total_logs, projects=projects, today=today)
    
    @app.route('/add_log', methods=['POST'])
    def add_log():
        """Add a new log entry."""
        project = request.form.get('project')
        description = request.form.get('description')
        date_str = request.form.get('date')
        
        if not description:
            return jsonify({'success': False, 'error': 'Description is required'}), 400
            
        if not project:
            project = "Misc"
        
        try:
            log_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        entry = LogEntry(
            id=None,
            project=project,
            description=description,
            date=log_date
        )
        
        log_id = db.add_log(entry)
        return jsonify({'success': True, 'id': log_id, 'message': 'Log entry added successfully'})
    
    @app.route('/update_log/<int:log_id>', methods=['POST'])
    def update_log(log_id):
        """Update a log entry."""
        project = request.form.get('project')
        description = request.form.get('description')
        date_str = request.form.get('date')
        
        if not description:
            return jsonify({'success': False, 'error': 'Description is required'}), 400
            
        if not project:
            project = "Misc"
            
        try:
            log_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
            
        if db.update_log(log_id, project, description, log_date):
            return jsonify({'success': True, 'message': 'Log entry updated'})
        else:
            return jsonify({'success': False, 'error': 'Log entry not found'}), 404

    @app.route('/delete_log/<int:log_id>', methods=['POST'])
    def delete_log(log_id):
        """Delete a log entry."""
        if db.delete_log(log_id):
            return jsonify({'success': True, 'message': 'Log entry deleted'})
        else:
            return jsonify({'success': False, 'error': 'Log entry not found'}), 404
    
    @app.route('/report/<mode>')
    def report(mode):
        """Generate and display a report."""
        if mode not in ['weekly', 'biweekly', 'monthly']:
            return "Invalid report mode", 400
        
        # Check settings for summarization
        summarize = False
        summary_points = "3-5"
        timeout = 120
        custom_instructions = ""
        verbosity = app.config.get('VERBOSITY', 0)
        
        # Template settings
        template_name = db.get_setting('report_template', 'classic')
        
        cline_avail = is_cline_available()
        enabled = False
        
        if mode == 'weekly':
            enabled = db.get_setting('ai_summary_weekly', 'false') == 'true'
        elif mode == 'biweekly':
            enabled = db.get_setting('ai_summary_biweekly', 'false') == 'true'
        elif mode == 'monthly':
            # Fallback to legacy setting if new one not set, but prioritize new key structure
            enabled = db.get_setting('ai_summary_monthly', 'false') == 'true'
            if not enabled and db.get_setting('ai_summary_enabled') == 'true':
                 enabled = True

        if enabled:
            summary_points = db.get_setting('ai_summary_points', '3-5')
            if not summary_points: # Handle empty string case
                summary_points = '3-5'
                
            custom_instructions = db.get_setting('ai_custom_instructions', '')
            try:
                timeout_val = db.get_setting('ai_timeout', '120')
                timeout = int(timeout_val) if timeout_val else 120
            except ValueError:
                timeout = 120
        
        # Collect provider settings
        provider_config = {
            'provider': db.get_setting('ai_provider', 'openai'),
            'api_key': db.get_setting('ai_api_key', ''),
            'model': db.get_setting('ai_model', ''),
            'base_url': db.get_setting('ai_base_url', '')
        }
        
        summarize = enabled 
        
        if summarize:
            logger.info(f"{mode.title()} report requested. Summarization: {summarize}")
            logger.debug(f"Provider: {provider_config['provider']}, Points: {summary_points}, Timeout: {timeout}")
        
        start_date, end_date = ReportGenerator.get_date_range(mode)
        logs = db.get_logs(start_date, end_date)
        
        logger.info(f"Found {len(logs)} logs for period {start_date} - {end_date}")
        
        # Generate summaries
        summaries = ReportGenerator.generate_summaries(
            logs, mode, summarize, verbosity, summary_points, timeout, provider_config
        )
        
        report_html = ReportGenerator.format_report_html(logs, mode, summaries, template_name)
        report_text = ReportGenerator.format_report(
            logs, mode, summaries, verbosity, custom_instructions, template_name, provider_config, timeout
        )
        
        return render_template('index.html', 
                             logs=db.get_logs(), 
                             projects=db.get_all_projects(),
                             report=report_html,
                             report_text=report_text,
                             report_mode=mode)
    
    @app.route('/settings')
    def settings():
        """Settings page."""
        return render_template('settings.html')
        
    @app.route('/api/settings', methods=['GET'])
    def get_settings():
        """Get all settings and system capabilities."""
        
        def safe_int(val, default):
            try:
                if not val: return default
                return int(val)
            except (ValueError, TypeError):
                return default

        settings = {
            # AI
            'ai_summary_weekly': db.get_setting('ai_summary_weekly', 'false') == 'true',
            'ai_summary_biweekly': db.get_setting('ai_summary_biweekly', 'false') == 'true',
            'ai_summary_monthly': db.get_setting('ai_summary_monthly', 'false') == 'true',
            'ai_summary_enabled': db.get_setting('ai_summary_enabled') == 'true', # Legacy/Master
            'ai_summary_points': db.get_setting('ai_summary_points', '3-5'),
            'ai_timeout': safe_int(db.get_setting('ai_timeout'), 120),
            'ai_custom_instructions': db.get_setting('ai_custom_instructions', ''),
            
            # Provider Settings
            'ai_provider': db.get_setting('ai_provider', 'openai'),
            'ai_api_key': db.get_setting('ai_api_key', ''),
            'ai_model': db.get_setting('ai_model', ''),
            'ai_base_url': db.get_setting('ai_base_url', ''),
            
            'cline_available': is_cline_available(),
            # Preferences
            'report_template': db.get_setting('report_template', 'classic'),
            'recent_logs_limit': safe_int(db.get_setting('recent_logs_limit'), 20),
            'auto_open_browser': db.get_setting('auto_open_browser', 'true') == 'true',
        }
        return jsonify(settings)
        
    @app.route('/api/settings', methods=['POST'])
    def update_settings():
        """Update settings."""
        data = request.json
        
        # AI Summarization Modes
        if 'ai_summary_weekly' in data:
            db.set_setting('ai_summary_weekly', 'true' if data['ai_summary_weekly'] else 'false')
        if 'ai_summary_biweekly' in data:
            db.set_setting('ai_summary_biweekly', 'true' if data['ai_summary_biweekly'] else 'false')
        if 'ai_summary_monthly' in data:
            db.set_setting('ai_summary_monthly', 'true' if data['ai_summary_monthly'] else 'false')
            db.set_setting('ai_summary_enabled', 'true' if data['ai_summary_monthly'] else 'false')

        if 'ai_summary_enabled' in data:
            db.set_setting('ai_summary_enabled', 'true' if data['ai_summary_enabled'] else 'false')
            
        if 'ai_summary_points' in data:
            db.set_setting('ai_summary_points', str(data['ai_summary_points']))
        if 'ai_timeout' in data:
            db.set_setting('ai_timeout', str(data['ai_timeout']))
        if 'ai_custom_instructions' in data:
            db.set_setting('ai_custom_instructions', str(data['ai_custom_instructions']))
            
        # Provider Settings
        if 'ai_provider' in data:
            db.set_setting('ai_provider', str(data['ai_provider']))
        if 'ai_api_key' in data:
            db.set_setting('ai_api_key', str(data['ai_api_key']))
        if 'ai_model' in data:
            db.set_setting('ai_model', str(data['ai_model']))
        if 'ai_base_url' in data:
            db.set_setting('ai_base_url', str(data['ai_base_url']))
            
        if 'report_template' in data:
            db.set_setting('report_template', str(data['report_template']))
        if 'recent_logs_limit' in data:
            db.set_setting('recent_logs_limit', str(data['recent_logs_limit']))
        if 'auto_open_browser' in data:
            db.set_setting('auto_open_browser', 'true' if data['auto_open_browser'] else 'false')

        return jsonify({'success': True})
    
    @app.route('/clear_all', methods=['POST'])
    def clear_all():
        """Clear all log entries."""
        db.clear_all()
        return jsonify({'success': True, 'message': 'All log entries cleared'})
    
    @app.route('/api/logs')
    def get_logs_api():
        """API endpoint to get logs as JSON."""
        logs = db.get_logs()
        return jsonify([log.to_dict() for log in logs])
    
    return app


def is_cline_available():
    """Check if cline CLI is available."""
    return shutil.which('cline') is not None


def open_browser(port=5000):
    """Open browser after a short delay."""
    url = f'http://127.0.0.1:{port}'
    webbrowser.open(url)


@click.command()
@click.option('--port', '-p', default=5000, help='Port to run the server on')
@click.option('--verbose', '-v', count=True, help='Enable verbose output (-v for info, -vv for full debug)')
@click.option('--no-browser', '-n', is_flag=True, help='Do not open browser automatically')
def main(port, verbose, no_browser):
    """Main entry point for fastrep-ui command."""
    setup_logging(verbose)
    app = create_app(verbose)
    
    print("=" * 60)
    print("FastRep Web UI Starting...")
    if verbose > 0:
        print(f"[VERBOSE] Verbosity level: {verbose}")
    print("=" * 60)
    print(f"\n🚀 Access the web interface at: http://127.0.0.1:{port}")
    print("\n📝 Features:")
    print("  • Add and manage work logs")
    print("  • Generate weekly, bi-weekly, and monthly reports")
    print("  • View and delete entries")
    print("\n⌨️  Press CTRL+C to stop the server\n")
    print("=" * 60)
    
    # Check DB setting for auto open
    db = Database()
    auto_open = db.get_setting('auto_open_browser', 'true') == 'true'
    
    if not no_browser and auto_open:
        # Check if we are in the main process (not reloader)
        if not os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            # Open browser after 1.5 seconds
            Timer(1.5, open_browser, args=[port]).start()
    
    app.run(debug=False, port=port, host='127.0.0.1')


if __name__ == '__main__':
    main()

from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os
import shutil
import webbrowser
import click
import logging
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
            limit = int(db.get_setting('recent_logs_limit', '20'))
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
        
        if mode == 'monthly':
            cline_avail = is_cline_available()
            enabled = db.get_setting('ai_summary_enabled') == 'true'
            summary_points = db.get_setting('ai_summary_points', '3-5')
            custom_instructions = db.get_setting('ai_custom_instructions', '')
            try:
                timeout = int(db.get_setting('ai_timeout', '120'))
            except ValueError:
                timeout = 120
                
            summarize = cline_avail and enabled
            
            logger.info(f"Monthly report requested. Summarization: {summarize}")
            logger.debug(f"Cline available: {cline_avail}, Enabled: {enabled}, Points: {summary_points}, Timeout: {timeout}")
        
        start_date, end_date = ReportGenerator.get_date_range(mode)
        logs = db.get_logs(start_date, end_date)
        
        logger.info(f"Found {len(logs)} logs for period {start_date} - {end_date}")
        
        # Generate summaries once
        summaries = ReportGenerator.generate_summaries(logs, mode, summarize, verbosity, summary_points, timeout)
        
        report_html = ReportGenerator.format_report_html(logs, mode, summaries, template_name)
        report_text = ReportGenerator.format_report(logs, mode, summaries, verbosity, custom_instructions, template_name)
        
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
        settings = {
            # AI
            'ai_summary_enabled': db.get_setting('ai_summary_enabled') == 'true',
            'ai_summary_points': db.get_setting('ai_summary_points', '3-5'),
            'ai_timeout': int(db.get_setting('ai_timeout', '120')),
            'ai_custom_instructions': db.get_setting('ai_custom_instructions', ''),
            'cline_available': is_cline_available(),
            # Preferences
            'report_template': db.get_setting('report_template', 'classic'),
            'recent_logs_limit': int(db.get_setting('recent_logs_limit', '20')),
            'auto_open_browser': db.get_setting('auto_open_browser', 'true') == 'true',
            # Reminders
            'reminder_enabled': db.get_setting('reminder_enabled', 'false') == 'true',
            'reminder_time': db.get_setting('reminder_time', '17:30'),
            'reminder_days': db.get_setting('reminder_days', '0,1,2,3,4').split(','),
        }
        return jsonify(settings)
        
    @app.route('/api/settings', methods=['POST'])
    def update_settings():
        """Update settings."""
        data = request.json
        if 'ai_summary_enabled' in data:
            db.set_setting('ai_summary_enabled', 'true' if data['ai_summary_enabled'] else 'false')
        if 'ai_summary_points' in data:
            db.set_setting('ai_summary_points', str(data['ai_summary_points']))
        if 'ai_timeout' in data:
            db.set_setting('ai_timeout', str(data['ai_timeout']))
        if 'ai_custom_instructions' in data:
            db.set_setting('ai_custom_instructions', str(data['ai_custom_instructions']))
            
        if 'report_template' in data:
            db.set_setting('report_template', str(data['report_template']))
        if 'recent_logs_limit' in data:
            db.set_setting('recent_logs_limit', str(data['recent_logs_limit']))
        if 'auto_open_browser' in data:
            db.set_setting('auto_open_browser', 'true' if data['auto_open_browser'] else 'false')
        
        # Reminder settings
        if 'reminder_enabled' in data:
            db.set_setting('reminder_enabled', 'true' if data['reminder_enabled'] else 'false')
        if 'reminder_time' in data:
            db.set_setting('reminder_time', data['reminder_time'])
        if 'reminder_days' in data:
            db.set_setting('reminder_days', ','.join(data['reminder_days']))

        # After saving settings, schedule the cron job
        schedule_reminder_job()

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


def schedule_reminder_job():
    """Update the system's scheduled task for reminders."""
    import subprocess
    db = Database()
    
    enabled = db.get_setting('reminder_enabled') == 'true'
    time_str = db.get_setting('reminder_time', '17:30')
    days = db.get_setting('reminder_days', '0,1,2,3,4')
    
    try:
        fastrep_path = shutil.which('fastrep')
        if not fastrep_path:
            logger.error("Could not find 'fastrep' executable in PATH.")
            return

        if sys.platform == 'win32':
            # Windows Task Scheduler
            task_name = "FastRepReminder"
            if enabled:
                hour, minute = time_str.split(':')
                day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
                days_str = ",".join([day_map[int(d)] for d in days.split(',')])
                
                # Note: schtasks requires admin to schedule for specific days.
                # /SC WEEKLY is more reliable without admin.
                # We will schedule it daily and the `fastrep notify` command will check the day.
                cmd = [
                    'schtasks', '/Create', '/TN', task_name,
                    '/TR', f'"{fastrep_path}" notify',
                    '/SC', 'DAILY', '/ST', time_str, '/F'
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info("Windows scheduled task updated.")
            else:
                # Delete task
                cmd = ['schtasks', '/Delete', '/TN', task_name, '/F']
                # Ignore errors if task doesn't exist
                subprocess.run(cmd, check=False, capture_output=True)
                logger.info("Windows scheduled task removed.")

        else:
            # Unix-like (macOS, Linux) with cron
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout
            
            new_crontab_lines = [
                line for line in current_crontab.splitlines() 
                if "fastrep notify" not in line and line.strip()
            ]
            
            if enabled:
                hour, minute = time_str.split(':')
                # Cron days are 0-6 (Sun-Sat) or 1-7 (Mon-Sun) depending on system.
                # Python is Mon=0, Sun=6. Cron is Sun=0 or 7.
                # To be safe, we let `fastrep notify` check the day.
                cron_job = f"{minute} {hour} * * * {fastrep_path} notify"
                new_crontab_lines.append(cron_job)
                
            new_crontab = "\n".join(new_crontab_lines) + "\n"
            subprocess.run(['crontab', '-'], input=new_crontab, text=True, check=True)
            logger.info(f"Cron job {'updated' if enabled else 'removed'}.")
            
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to update scheduled task: {e}")


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

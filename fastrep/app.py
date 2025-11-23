from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os
import shutil
import webbrowser
import click
from threading import Timer
from .database import Database
from .models import LogEntry
from .report_generator import ReportGenerator


def create_app(verbose=False):
    """Create and configure Flask application."""
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'ui', 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'ui', 'static'))
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['VERBOSE'] = verbose
    
    db = Database()
    
    @app.route('/')
    def index():
        """Main page with log entry form and recent logs."""
        logs = db.get_logs()
        projects = db.get_all_projects()
        today = datetime.now().strftime('%Y-%m-%d')
        return render_template('index.html', logs=logs, projects=projects, today=today)
    
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
        verbose = app.config.get('VERBOSE', False)
        
        if mode == 'monthly':
            cline_avail = is_cline_available()
            enabled = db.get_setting('ai_summary_enabled') == 'true'
            summarize = cline_avail and enabled
            
            if verbose:
                print(f"[VERBOSE] Monthly report requested. Summarization: {summarize}")
                print(f"[VERBOSE] Cline available: {cline_avail}, Enabled setting: {enabled}")
        
        start_date, end_date = ReportGenerator.get_date_range(mode)
        logs = db.get_logs(start_date, end_date)
        
        if verbose:
            print(f"[VERBOSE] Found {len(logs)} logs for period {start_date} - {end_date}")
        
        report_html = ReportGenerator.format_report_html(logs, mode, summarize, verbose)
        report_text = ReportGenerator.format_report(logs, mode, summarize, verbose)
        
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
            'ai_summary_enabled': db.get_setting('ai_summary_enabled') == 'true',
            'cline_available': is_cline_available()
        }
        return jsonify(settings)
        
    @app.route('/api/settings', methods=['POST'])
    def update_settings():
        """Update settings."""
        data = request.json
        if 'ai_summary_enabled' in data:
            db.set_setting('ai_summary_enabled', 'true' if data['ai_summary_enabled'] else 'false')
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
    
    # Try to open in app mode if possible (Chrome/Chromium)
    try:
        # Common browser commands with app mode argument
        browser_commands = [
            ['google-chrome', '--app=' + url],
            ['chromium-browser', '--app=' + url],
            ['chromium', '--app=' + url],
            ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--app=' + url]
        ]
        
        import subprocess
        for cmd in browser_commands:
            try:
                # Check if executable exists (except for mac app path)
                if cmd[0].startswith('/') and os.path.exists(cmd[0]):
                    subprocess.Popen(cmd)
                    return
                
                # For commands in path, this check is harder without 'which', 
                # so we just try to execute and catch exception
                if not cmd[0].startswith('/'):
                    subprocess.Popen(cmd)
                    return
            except FileNotFoundError:
                continue
            except Exception:
                continue
                
    except Exception:
        pass
        
    # Fallback to default browser
    webbrowser.open(url)


@click.command()
@click.option('--port', '-p', default=5000, help='Port to run the server on')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output for debugging')
def main(port, verbose):
    """Main entry point for fastrep-ui command."""
    app = create_app(verbose)
    
    print("=" * 60)
    print("FastRep Web UI Starting...")
    if verbose:
        print("[VERBOSE] Verbose mode enabled")
    print("=" * 60)
    print(f"\n🚀 Access the web interface at: http://127.0.0.1:{port}")
    print("\n📝 Features:")
    print("  • Add and manage work logs")
    print("  • Generate weekly, bi-weekly, and monthly reports")
    print("  • View and delete entries")
    print("\n⌨️  Press CTRL+C to stop the server\n")
    print("=" * 60)
    
    # Open browser after 1.5 seconds
    Timer(1.5, open_browser, args=[port]).start()
    
    app.run(debug=False, port=port, host='127.0.0.1')


if __name__ == '__main__':
    main()

import click
import subprocess
import sys
from datetime import datetime
from .database import Database
from .models import LogEntry
from .report_generator import ReportGenerator


@click.group()
def cli():
    """FastRep - Track your daily work activities and generate reports."""
    pass


@cli.command()
@click.option('--project', '-p', default="Misc", help='Project name')
@click.option('--description', '-d', required=True, help='Work description')
@click.option('--date', '-dt', default=None, help='Date (YYYY-MM-DD), defaults to today')
def log(project, description, date):
    """Add a new work log entry."""
    db = Database()
    
    if date:
        try:
            log_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            click.echo("Error: Date must be in YYYY-MM-DD format", err=True)
            return
    else:
        log_date = datetime.now()
    
    entry = LogEntry(
        id=None,
        project=project,
        description=description,
        date=log_date
    )
    
    log_id = db.add_log(entry)
    click.echo(f"✓ Log entry added successfully (ID: {log_id})")
    click.echo(f"  Project: {project}")
    click.echo(f"  Date: {log_date.strftime('%Y-%m-%d')}")
    click.echo(f"  Description: {description}")


@cli.command()
@click.option('--mode', '-m', 
              type=click.Choice(['weekly', 'biweekly', 'monthly'], case_sensitive=False),
              default='weekly',
              help='Report period (weekly/biweekly/monthly)')
@click.option('--start', '-s', default=None, help='Custom start date (YYYY-MM-DD)')
@click.option('--end', '-e', default=None, help='Custom end date (YYYY-MM-DD)')
def view(mode, start, end):
    """View logs and generate reports."""
    db = Database()
    
    if start or end:
        # Custom date range
        start_date = datetime.strptime(start, '%Y-%m-%d') if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d') if end else None
        logs = db.get_logs(start_date, end_date)
        report = ReportGenerator.format_report(logs)
    else:
        # Use predefined mode
        start_date, end_date = ReportGenerator.get_date_range(mode)
        logs = db.get_logs(start_date, end_date)
        report = ReportGenerator.format_report(logs, mode)
    
    click.echo(report)


@cli.command()
@click.option('--id', '-i', required=True, type=int, help='Log entry ID to delete')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation prompt')
def delete(id, confirm):
    """Delete a log entry by ID."""
    db = Database()
    
    if not confirm:
        if not click.confirm(f'Are you sure you want to delete log entry #{id}?'):
            click.echo('Deletion cancelled.')
            return
    
    if db.delete_log(id):
        click.echo(f'✓ Log entry #{id} deleted successfully.')
    else:
        click.echo(f'✗ Log entry #{id} not found.', err=True)


@cli.command()
def list():
    """List all log entries."""
    db = Database()
    logs = db.get_logs()
    
    if not logs:
        click.echo("No log entries found.")
        return
    
    click.echo(f"\n{'ID':<6} {'Date':<12} {'Project':<20} {'Description'}")
    click.echo("-" * 80)
    
    for log in logs:
        desc = log.description[:40] + "..." if len(log.description) > 40 else log.description
        click.echo(f"{log.id:<6} {log.date.strftime('%Y-%m-%d'):<12} {log.project:<20} {desc}")
    
    click.echo(f"\nTotal entries: {len(logs)}")


@cli.command()
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation prompt')
def clear(confirm):
    """Clear all log entries from database."""
    if not confirm:
        if not click.confirm('⚠️  This will delete ALL log entries. Are you sure?'):
            click.echo('Clear operation cancelled.')
            return
    
    db = Database()
    db.clear_all()
    click.echo('✓ All log entries cleared successfully.')


@cli.command()
def projects():
    """List all projects."""
    db = Database()
    projects = db.get_all_projects()
    
    if not projects:
        click.echo("No projects found.")
        return
    
    click.echo("\nProjects:")
    click.echo("-" * 40)
    for project in projects:
        click.echo(f"  • {project}")
    click.echo(f"\nTotal projects: {len(projects)}")


if __name__ == '__main__':
    cli()

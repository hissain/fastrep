from datetime import datetime, timedelta
from typing import List
from collections import defaultdict
from .models import LogEntry


class ReportGenerator:
    """Generate formatted reports from log entries."""
    
    @staticmethod
    def get_date_range(mode: str) -> tuple:
        """Get start and end dates based on report mode."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if mode == 'weekly':
            start_date = today - timedelta(days=6)
            end_date = today
        elif mode == 'biweekly':
            start_date = today - timedelta(days=13)
            end_date = today
        elif mode == 'monthly':
            # Get first day of current month
            start_date = today.replace(day=1)
            end_date = today
        else:
            raise ValueError(f"Unknown report mode: {mode}")
        
        return start_date, end_date
    
    @staticmethod
    def group_by_project(logs: List[LogEntry]) -> dict:
        """Group logs by project."""
        grouped = defaultdict(list)
        for log in logs:
            grouped[log.project].append(log)
        
        # Sort each project's logs by date (descending)
        for project in grouped:
            grouped[project].sort(key=lambda x: x.date, reverse=True)
        
        return dict(grouped)
    
    @staticmethod
    def format_report(logs: List[LogEntry], mode: str = None) -> str:
        """Format logs into a readable report."""
        if not logs:
            return "No logs found for this period."
        
        grouped = ReportGenerator.group_by_project(logs)
        
        report_lines = []
        
        if mode:
            start_date, end_date = ReportGenerator.get_date_range(mode)
            report_lines.append(f"Report Period: {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}")
            report_lines.append("=" * 60)
            report_lines.append("")
        
        for project in sorted(grouped.keys()):
            report_lines.append(f"Project: {project}")
            report_lines.append("-" * 60)
            
            for log in grouped[project]:
                date_str = log.date.strftime('%m/%d')
                report_lines.append(f"  * {date_str} - {log.description}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def format_report_html(logs: List[LogEntry], mode: str = None) -> str:
        """Format logs into HTML report."""
        if not logs:
            return "<p>No logs found for this period.</p>"
        
        grouped = ReportGenerator.group_by_project(logs)
        
        html_parts = []
        
        if mode:
            start_date, end_date = ReportGenerator.get_date_range(mode)
            html_parts.append(f"<p><strong>Report Period:</strong> {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}</p>")
        
        for project in sorted(grouped.keys()):
            html_parts.append(f"<h4>{project}</h4>")
            html_parts.append("<ul>")
            
            for log in grouped[project]:
                date_str = log.date.strftime('%m/%d')
                html_parts.append(f"<li><strong>{date_str}</strong> - {log.description}</li>")
            
            html_parts.append("</ul>")
        
        return "".join(html_parts)
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict
import subprocess
import tempfile
import os
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
            start_date = today - timedelta(days=30)
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
    def summarize_project_logs(project: str, logs: List[LogEntry], verbose: bool = False) -> List[str]:
        """Summarize logs using cline CLI."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
            output_file = tmp.name
            
        logs_text = "\n".join([f"- {log.date.strftime('%Y-%m-%d')}: {log.description}" for log in logs])
        
        prompt = (
            f"Summarize the following work logs for project '{project}' into 3-5 concise bullet points. "
            f"Focus on key achievements and tasks. "
            f"Each bullet point MUST include the relevant date or date range (e.g., '11/15 - Implemented X' or '11/15-11/17 - Fixed Y'). "
            f"Ensure the text is grammatically correct and professional. "
            f"Write ONLY the bullet points to the file '{output_file}'. "
            f"Do not include any other text or conversation.\n\n"
            f"Logs:\n{logs_text}"
        )
        
        if verbose:
            print(f"\n[VERBOSE] Summarizing project: {project}")
            print(f"[VERBOSE] Prompt length: {len(prompt)} chars")
            print(f"[VERBOSE] Output file: {output_file}")
            print(f"[VERBOSE] Executing: cline [prompt] --yolo --mode act")
        
        try:
            # Call cline CLI
            result = subprocess.run(['cline', prompt, '--yolo', '--mode', 'act'], 
                         check=True, 
                         capture_output=True,
                         text=True)
            
            if verbose:
                print(f"[VERBOSE] CLI Return Code: {result.returncode}")
                if result.stdout:
                    print(f"[VERBOSE] CLI Stdout (truncated): {result.stdout[:200]}...")
                if result.stderr:
                    print(f"[VERBOSE] CLI Stderr (truncated): {result.stderr[:200]}...")
            
            # Read result
            with open(output_file, 'r') as f:
                summary = f.read().strip()
                
            if summary:
                if verbose:
                    print(f"[VERBOSE] Summary obtained ({len(summary)} chars)")
                return summary.split('\n')
            else:
                if verbose:
                    print(f"[VERBOSE] Warning: Summary file was empty")
                    
        except Exception as e:
            print(f"Error summarizing logs for {project}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
                
        # Fallback if summarization fails
        if verbose:
            print(f"[VERBOSE] Falling back to raw logs for {project}")
        return [f"{log.date.strftime('%m/%d')} - {log.description}" for log in logs]

    @staticmethod
    def improve_report_text(report_text: str, verbose: bool = False) -> str:
        """Improve the grammar and tone of the full report text."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
            output_file = tmp.name
            
        prompt = (
            f"Review and improve the following work report. "
            f"Ensure correct grammar, professional tone, and consistency. "
            f"Do NOT remove any information, dates, or projects. "
            f"Write the improved report to the file '{output_file}'. "
            f"Do not include any other text or conversation.\n\n"
            f"Report:\n{report_text}"
        )
        
        if verbose:
            print(f"\n[VERBOSE] Improving full report text")
            print(f"[VERBOSE] Prompt length: {len(prompt)} chars")
        
        try:
            subprocess.run(['cline', prompt, '--yolo', '--mode', 'act'], 
                         check=True, 
                         capture_output=True,
                         text=True)
            
            with open(output_file, 'r') as f:
                improved_text = f.read().strip()
                
            if improved_text:
                if verbose:
                    print(f"[VERBOSE] Report improved successfully")
                return improved_text
                
        except Exception as e:
            print(f"Error improving report: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
                
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
                
        return report_text

    @staticmethod
    def format_report(logs: List[LogEntry], mode: str = None, summarize: bool = False, verbose: bool = False) -> str:
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
            
            project_logs = grouped[project]
            
            should_summarize = summarize and len(project_logs) > 5
            
            if verbose:
                print(f"[VERBOSE] Project: {project}, Logs: {len(project_logs)}, Should summarize: {should_summarize}")
            
            if should_summarize:
                report_lines.append("(AI Summary)")
                summary_lines = ReportGenerator.summarize_project_logs(project, project_logs, verbose)
                for line in summary_lines:
                    report_lines.append(f"  {line}")
            else:
                for log in project_logs:
                    date_str = log.date.strftime('%m/%d')
                    report_lines.append(f"  * {date_str} - {log.description}")
            
            report_lines.append("")
        
        final_text = "\n".join(report_lines)
        
        if summarize:
            return ReportGenerator.improve_report_text(final_text, verbose)
            
        return final_text
    
    @staticmethod
    def format_report_html(logs: List[LogEntry], mode: str = None, summarize: bool = False, verbose: bool = False) -> str:
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
            
            project_logs = grouped[project]
            
            should_summarize = summarize and len(project_logs) > 5
            
            if verbose:
                print(f"[VERBOSE] HTML - Project: {project}, Logs: {len(project_logs)}, Should summarize: {should_summarize}")
            
            if should_summarize:
                html_parts.append("<p><em>(AI Summary)</em></p>")
                html_parts.append("<ul>")
                summary_lines = ReportGenerator.summarize_project_logs(project, project_logs, verbose)
                for line in summary_lines:
                    # Clean up bullet points if they exist in the output
                    line = line.lstrip('-*• ')
                    html_parts.append(f"<li>{line}</li>")
                html_parts.append("</ul>")
            else:
                html_parts.append("<ul>")
                for log in project_logs:
                    date_str = log.date.strftime('%m/%d')
                    html_parts.append(f"<li><strong>{date_str}</strong> - {log.description}</li>")
                html_parts.append("</ul>")
        
        return "".join(html_parts)

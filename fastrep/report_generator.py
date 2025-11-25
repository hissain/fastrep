from datetime import datetime, timedelta
from typing import List
from collections import defaultdict
import subprocess
import tempfile
import os
import logging
import time
from .models import LogEntry
from .llm import get_llm_client

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate formatted reports from log entries."""

    TEMPLATES = {
        'classic': {
            'name': 'Classic',
            'description': 'Standard format with date range header.',
            'date_format': '%m/%d',
            'show_header': True,
            'html_item': '<li><strong>{date}</strong> - {description}</li>',
            'text_item': '  * {date} - {description}'
        },
        'classic_clean': {
            'name': 'Classic (No Header)',
            'description': 'Standard format without date range header.',
            'date_format': '%m/%d',
            'show_header': False,
            'html_item': '<li><strong>{date}</strong> - {description}</li>',
            'text_item': '  * {date} - {description}'
        },
        'bold': {
            'name': 'Bold Dates',
            'description': 'Dates bolded at start.',
            'date_format': '%Y-%m-%d',
            'show_header': True,
            'html_item': '<li><b style="color:var(--primary-color)">{date}</b>: {description}</li>',
            'text_item': '  * **{date}**: {description}'
        },
        'modern': {
            'name': 'Modern',
            'description': 'Description first, italic date at end.',
            'date_format': '%b %d',
            'show_header': True,
            'html_item': '<li>{description} <em style="color:var(--text-secondary)">({date})</em></li>',
            'text_item': '  * {description} ({date})'
        },
        'professional': {
            'name': 'Professional',
            'description': 'Detailed date badges.',
            'date_format': '%A, %B %d',
            'show_header': True,
            'html_item': '<li><span class="badge" style="background:#64748b">{date}</span> {description}</li>',
            'text_item': '  * [{date}] {description}'
        },
        'professional_clean': {
            'name': 'Professional (No Header)',
            'description': 'Detailed badges without range header.',
            'date_format': '%A, %B %d',
            'show_header': False,
            'html_item': '<li><span class="badge" style="background:#64748b">{date}</span> {description}</li>',
            'text_item': '  * [{date}] {description}'
        },
        'compact': {
            'name': 'Compact',
            'description': 'Minimalist layout.',
            'date_format': '%m/%d',
            'show_header': False,
            'html_item': '<li><small style="color:var(--text-secondary)">{date}</small> {description}</li>',
            'text_item': '  - {date} {description}'
        }
    }
    
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
    def _get_date_format_instruction(template_name: str) -> str:
        """Get date format instruction for LLM based on template."""
        template = ReportGenerator.TEMPLATES.get(template_name, ReportGenerator.TEMPLATES['classic'])
        fmt = template['date_format']
        
        if fmt == '%m/%d':
            return "MM/DD (e.g. 11/23)"
        elif fmt == '%Y-%m-%d':
            return "YYYY-MM-DD (e.g. 2025-11-23)"
        elif fmt == '%b %d':
            return "Mon DD (e.g. Oct 23)"
        elif 'A' in fmt:
            return "Weekday, Month DD (e.g. Monday, October 23)"
        return "MM/DD"

    @staticmethod
    def generate_summaries(logs: List[LogEntry], mode: str, summarize: bool, verbosity: int = 0, summary_points: str = "3-5", timeout: int = 120, provider_config: dict = None, threshold: int = 5, custom_instructions: str = "", template_name: str = "classic") -> dict:
        """Generate AI summaries for projects if needed."""
        if not summarize:
            return {}
            
        grouped = ReportGenerator.group_by_project(logs)
        # We process ALL projects, but instructions differ based on count
        projects_to_process = grouped
        
        if not projects_to_process:
            return {}

        # Construct a single prompt for all projects
        date_format_desc = ReportGenerator._get_date_format_instruction(template_name)
        
        instruction = (
            "You are a professional project manager generating a monthly work report. "
            "Your task is to process the raw work logs for multiple projects. "
            f"For projects with MANY logs (more than {threshold}), summarize them into {summary_points} concise bullet points focusing on key achievements. "
            f"For projects with FEW logs (less than or equal to {threshold}), simply polish the existing entries for grammar and professional tone, keeping the original detail. "
            f"Each output item MUST include a specific date or date range formatted strictly as {date_format_desc}. "
            f"For date ranges, use the format '{date_format_desc} - {date_format_desc}'. "
            "Ensure consistent professional tone across all projects. "
        )

        if custom_instructions:
            instruction += f"\n\nAdditional Instructions: {custom_instructions}"

        instruction += (
            "\n\nIMPORTANT: Return the output as a valid JSON object where keys are Project names and values are LISTS OF OBJECTS. "
            "Each object must have two keys: 'date' (string) and 'description' (string). "
            "Example: { 'Project A': [ {'date': '11/15', 'description': 'Completed task X'} ] }"
            "\nDo not include markdown formatting like ```json."
        )
        
        prompt_logs = ""
        for project, p_logs in projects_to_process.items():
            prompt_logs += f"\nProject: {project}\n"
            prompt_logs += "\n".join([f"- {log.date.strftime('%Y-%m-%d')}: {log.description}" for log in p_logs])
            prompt_logs += "\n"
            
        full_prompt = f"{instruction}\n\nData:\n{prompt_logs}"
        
        logger.info(f"Generating report content for {len(projects_to_process)} projects in a single call")
        if verbosity >= 2:
            logger.debug(f"Full Prompt:\n{full_prompt}")
        
        response_text = ""
        
        # Try Direct Provider
        if provider_config and provider_config.get('api_key'):
            try:
                client = get_llm_client(
                    provider_config['provider'], 
                    provider_config['api_key'], 
                    provider_config['model'], 
                    provider_config['base_url']
                )
                if client:
                    response_text = client.generate(full_prompt, "You are a precise JSON generator.")
            except Exception as e:
                logger.error(f"Provider processing failed: {e}")

        # Fallback to Cline CLI
        if not response_text:
            temp_dir = os.path.join(os.path.expanduser("~"), ".fastrep", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            output_file = os.path.join(temp_dir, f"report_all_{int(time.time())}.json")
            
            cli_prompt = f"{full_prompt}\n\nWrite the JSON to '{output_file}'. No other text."
            
            try:
                # Increase timeout for batch processing
                batch_timeout = max(timeout * 2, 300) 
                subprocess.run(['cline', cli_prompt, '--yolo', '--mode', 'act'], 
                            check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=batch_timeout)
                
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        response_text = f.read().strip()
                    os.remove(output_file)
            except Exception as e:
                logger.error(f"CLI processing failed: {e}")

        if verbosity >= 2:
            logger.debug(f"AI Response:\n{response_text}")

        # Parse JSON
        try:
            if response_text:
                # Clean potential markdown
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                import json
                return json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to parse AI JSON: {e}")
            if verbosity >= 1:
                logger.warning(f"Raw response was: {response_text[:500]}...")
            
        return {}

    @staticmethod
    def format_report(logs: List[LogEntry], mode: str = None, summaries: dict = None, verbosity: int = 0, custom_instructions: str = "", template_name: str = 'classic', provider_config: dict = None, timeout: int = 120) -> str:
        """Format logs into a readable report."""
        if not logs:
            return "No logs found for this period."
        
        grouped = ReportGenerator.group_by_project(logs)
        summaries = summaries or {}
        template = ReportGenerator.TEMPLATES.get(template_name, ReportGenerator.TEMPLATES['classic'])
        
        report_lines = []
        
        if mode and template.get('show_header', True):
            start_date, end_date = ReportGenerator.get_date_range(mode)
            report_lines.append(f"Report Period: {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}")
            report_lines.append("=" * 60)
            report_lines.append("")
        
        for project in sorted(grouped.keys()):
            report_lines.append(f"Project: {project}")
            report_lines.append("-" * 60)
            
            project_logs = grouped[project]
            
            # Use AI content if available for this project (it serves as both summary and polished raw logs now)
            if project in summaries:
                # report_lines.append("(AI Summary)") # Optional: Remove marker since it might be polished raw logs
                for item in summaries[project]:
                    if isinstance(item, dict) and 'date' in item and 'description' in item:
                        formatted_line = template['text_item'].format(date=item['date'], description=item['description'])
                        report_lines.append(formatted_line)
                    else:
                        report_lines.append(f"  * {str(item)}")
            else:
                # Fallback to raw if AI failed for this project
                for log in project_logs:
                    date_str = log.date.strftime(template['date_format'])
                    formatted_line = template['text_item'].format(date=date_str, description=log.description)
                    report_lines.append(formatted_line)
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def format_report_html(logs: List[LogEntry], mode: str = None, summaries: dict = None, template_name: str = 'classic') -> str:
        """Format logs into HTML report."""
        if not logs:
            return "<p>No logs found for this period.</p>"
        
        grouped = ReportGenerator.group_by_project(logs)
        summaries = summaries or {}
        template = ReportGenerator.TEMPLATES.get(template_name, ReportGenerator.TEMPLATES['classic'])
        
        html_parts = []
        
        if mode and template.get('show_header', True):
            start_date, end_date = ReportGenerator.get_date_range(mode)
            html_parts.append(f"<p><strong>Report Period:</strong> {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}</p>")
        
        for project in sorted(grouped.keys()):
            html_parts.append(f"<h4>{project}</h4>")
            
            project_logs = grouped[project]
            
            if project in summaries:
                # html_parts.append("<p><em>(AI Summary)</em></p>")
                html_parts.append("<ul>")
                for item in summaries[project]:
                    if isinstance(item, dict) and 'date' in item and 'description' in item:
                        formatted_line = template['html_item'].format(date=item['date'], description=item['description'])
                        html_parts.append(formatted_line)
                    else:
                        line = str(item).lstrip('-*• ')
                        html_parts.append(f"<li>{line}</li>")
                html_parts.append("</ul>")
            else:
                html_parts.append("<ul>")
                for log in project_logs:
                    date_str = log.date.strftime(template['date_format'])
                    formatted_line = template['html_item'].format(date=date_str, description=log.description)
                    html_parts.append(formatted_line)
                html_parts.append("</ul>")
        
        return "".join(html_parts)

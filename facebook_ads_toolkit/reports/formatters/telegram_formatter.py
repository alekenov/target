"""
Telegram-specific formatter for reports.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .text_formatter import TextFormatter

class TelegramFormatter(TextFormatter):
    def __init__(self):
        super().__init__()
        self.max_message_length = 4096  # Telegram's message length limit
        
    def format_report(self, data: Dict[str, Any], report_type: str) -> List[str]:
        """Format report data into Telegram messages."""
        if report_type == "hourly":
            return self._format_hourly_report(data)
        elif report_type == "daily":
            return self._format_daily_report(data)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
            
    def _format_hourly_report(self, data: Dict[str, Any]) -> List[str]:
        """Format hourly report for Telegram."""
        report = [
            "🕒 *Facebook Ads Hourly Report*",
            f"📅 {data['start_time'].strftime('%Y-%m-%d %H:%M')} - {data['end_time'].strftime('%H:%M')}\n"
        ]
        
        # Overall metrics
        report.extend([
            "📊 *Overall Performance*",
            f"💰 Spend: {self.format_currency(data['total_spend'])} "
            f"({self.format_change(data['total_spend'], data['previous_spend'], 2)})",
            f"👁 Impressions: {self.format_number(data['total_impressions'])} "
            f"({self.format_change(data['total_impressions'], data['previous_impressions'])})",
            f"🎯 CTR: {self.format_percentage(data['ctr'])} "
            f"({self.format_change(data['ctr'], data['previous_ctr'], 2, '%')})",
            f"💵 CPC: {self.format_currency(data['cpc'])} "
            f"({self.format_change(data['cpc'], data['previous_cpc'], 2)})\n"
        ])
        
        # Campaign groups
        for objective, campaigns in data['campaigns_by_objective'].items():
            report.extend([
                f"🎯 *{self._get_objective_name(objective)}*",
                "```",  # Start of monospace block for table
                "Campaign      Spend    CTR    CPC ",
                "─" * 40
            ])
            
            for campaign in campaigns:
                name = campaign['name'][:15]  # Truncate long names
                spend = self.format_currency(campaign['spend'])
                ctr = self.format_percentage(campaign['ctr'])
                cpc = self.format_currency(campaign['cpc'])
                
                report.append(f"{name:<15} {spend:>8} {ctr:>6} {cpc:>6}")
                
            report.extend([
                "```\n"  # End of monospace block
            ])
        
        # Join all lines and split into Telegram-sized messages
        full_report = "\n".join(report)
        return self.split_long_message(full_report)
        
    def _format_daily_report(self, data: Dict[str, Any]) -> List[str]:
        """Format daily report for Telegram."""
        report = [
            "📈 *Facebook Ads Daily Report*",
            f"📅 {data['date'].strftime('%Y-%m-%d')}\n"
        ]
        
        # Overall metrics
        report.extend([
            "📊 *Daily Summary*",
            f"💰 Total Spend: {self.format_currency(data['total_spend'])}",
            f"👁 Total Impressions: {self.format_number(data['total_impressions'])}",
            f"🎯 Average CTR: {self.format_percentage(data['average_ctr'])}",
            f"💵 Average CPC: {self.format_currency(data['average_cpc'])}",
            f"✨ Total Conversions: {self.format_number(data['total_conversions'])}\n"
        ])
        
        # Performance by objective
        report.append("🎯 *Performance by Objective*")
        for objective, metrics in data['objective_metrics'].items():
            report.extend([
                f"\n*{self._get_objective_name(objective)}*",
                "```",  # Start of monospace block for better formatting
                f"Spend: {self.format_currency(metrics['spend'])}",
                f"CTR:   {self.format_percentage(metrics['ctr'])}",
                f"CPC:   {self.format_currency(metrics['cpc'])}",
                "```"
            ])
        
        # Top performing campaigns
        report.extend([
            "\n🏆 *Top Performing Campaigns*",
            "```",  # Start of monospace block for table
            "Campaign         CTR     Conv.",
            "─" * 35
        ])
        
        for campaign in data['top_campaigns'][:5]:  # Show top 5
            name = campaign['name'][:15]  # Truncate long names
            ctr = self.format_percentage(campaign['ctr'])
            conv = str(campaign['conversions'])
            report.append(f"{name:<15} {ctr:>7} {conv:>6}")
            
        report.append("```")  # End of monospace block
        
        # Join all lines and split into Telegram-sized messages
        full_report = "\n".join(report)
        return self.split_long_message(full_report)
        
    def _get_objective_name(self, objective: str) -> str:
        """Convert objective code to display name."""
        objective_names = {
            'MESSAGES': 'Messages',
            'OUTCOME_TRAFFIC': 'Traffic',
            'OUTCOME_LEADS': 'Leads',
            'OUTCOME_ENGAGEMENT': 'Engagement',
            'UNKNOWN': 'Other'
        }
        return objective_names.get(objective, objective)

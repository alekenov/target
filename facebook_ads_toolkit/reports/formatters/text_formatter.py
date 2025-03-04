"""
Base text formatter for reports.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

class TextFormatter(ABC):
    def __init__(self):
        self.max_message_length = 4096  # Default max length for most messaging platforms
        
    def format_currency(self, amount: float) -> str:
        """Format currency values."""
        return f"${amount:.2f}"
        
    def format_percentage(self, value: float) -> str:
        """Format percentage values."""
        return f"{value:.2f}%"
        
    def format_number(self, value: int) -> str:
        """Format large numbers with thousands separator."""
        return f"{value:,}"
        
    def format_change(self, current: float, previous: float, 
                     decimals: int = 0, suffix: str = '') -> str:
        """Format value change with trend indicator."""
        if previous == 0:
            change_pct = 100 if current > 0 else 0
        else:
            change_pct = ((current - previous) / abs(previous)) * 100
            
        if change_pct > 0:
            indicator = "▲"
        elif change_pct < 0:
            indicator = "▼"
        else:
            indicator = "→"
            
        value = current - previous
        if decimals > 0:
            return f"{indicator} {abs(value):.{decimals}f}{suffix}"
        return f"{indicator} {abs(int(value))}{suffix}"
        
    def split_long_message(self, message: str) -> List[str]:
        """Split long message into chunks respecting message length limits."""
        if len(message) <= self.max_message_length:
            return [message]
            
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split by lines to preserve formatting
        lines = message.split('\n')
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            if current_length + line_length > self.max_message_length:
                # If current chunk is not empty, save it
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # If single line is longer than max length, split it
                if line_length > self.max_message_length:
                    while line:
                        chunk = line[:self.max_message_length]
                        chunks.append(chunk)
                        line = line[self.max_message_length:]
                else:
                    current_chunk.append(line)
                    current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # Add remaining chunk if any
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks
        
    @abstractmethod
    def format_report(self, data: Dict[str, Any], report_type: str) -> List[str]:
        """Format report data into a list of messages."""
        pass

import streamlit as st
import sys
from contextlib import contextmanager
from io import StringIO
import re

class StreamlitProcessOutput:
    """Class to handle capturing and displaying process output in Streamlit."""
    
    def __init__(self, container):
        self.container = container
        self.output_text = ""
        self.seen_lines = set()
        
    def clean_text(self, text):
        """Clean ANSI codes and formatting from text."""
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Clean up other formatting
        text = text.replace('[1m', '').replace('[95m', '').replace('[92m', '').replace('[00m', '')
        return text
        
    def write(self, text):
        """Write text to the Streamlit container."""
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            return
            
        # Split into lines and process each line
        lines = cleaned_text.split('\n')
        new_lines = []
        
        for line in lines:
            line = line.strip()
            if line and line not in self.seen_lines:
                self.seen_lines.add(line)
                new_lines.append(line)
        
        if new_lines:
            # Add the new lines to the output
            new_content = '\n'.join(new_lines)
            self.output_text = f"{self.output_text}\n{new_content}" if self.output_text else new_content
            
            # Update the display
            self.container.text(self.output_text)
        
    def flush(self):
        """Implement flush method required for stream compatibility."""
        pass

@contextmanager
def capture_output(container):
    """Capture stdout and redirect it to a Streamlit container.
    
    Usage:
        with capture_output(st.container()):
            # Code that prints to stdout
    """
    string_io = StringIO()
    output_handler = StreamlitProcessOutput(container)
    old_stdout = sys.stdout
    sys.stdout = output_handler
    try:
        yield string_io
    finally:
        sys.stdout = old_stdout

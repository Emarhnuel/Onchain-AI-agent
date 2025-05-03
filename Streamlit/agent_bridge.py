import sys
import os

# Add the absolute path to the onchain_agent directory
onchain_agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "onchain_agent", "src")
sys.path.append(onchain_agent_path)

# Import after path is set
from onchain_agent.crew import OnchainAgentCrew
from output_handler import capture_output
import streamlit as st
from pathlib import Path

def run_onchain_analysis(wallet_address: str, networks: str, output_container=None):
    """
    Run the Onchain AI Agent analysis with the given parameters.
    
    Args:
        wallet_address: The wallet address to analyze
        networks: Comma-separated string of networks to analyze
        output_container: Optional Streamlit container to capture output
    
    Returns:
        The result of the analysis
    """
    # Prepare inputs
    inputs = {
        'wallet_address': wallet_address,
        'networks': networks
    }
    
    # Create output directories if they don't exist
    Path("outputs").mkdir(exist_ok=True, parents=True)
    Path("memory").mkdir(exist_ok=True, parents=True)
    
    # Initialize crew
    crew = OnchainAgentCrew()
    
    # Run with or without output capturing
    if output_container:
        with capture_output(output_container):
            result = crew.crew().kickoff(inputs=inputs)
    else:
        result = crew.crew().kickoff(inputs=inputs)
    
    return result

def get_report_content():
    """
    Read the generated report content from the output file.
    
    Returns:
        str: The report content as a string, or None if no report was found
    """
    report_path = Path("outputs/onchain_intelligence_report.md")
    
    if not report_path.exists():
        return None
    
    try:
        with open(report_path, "r") as file:
            return file.read()
    except Exception as e:
        st.error(f"Error reading report: {str(e)}")
        return None

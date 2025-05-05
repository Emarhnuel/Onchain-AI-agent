#!/usr/bin/env python
import sys
import warnings
import os
from datetime import datetime

from onchain_agent.crew import OnchainAgentCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Main execution file for the Onchain AI Agent System
# Keeps main execution flow in main.py as per project rules

def run():
    """
    Run the Onchain AI Agent crew for blockchain analysis.
    
    This function initializes the crew with the necessary inputs,
    including wallet addresses and networks to analyze.
    """
    # Sample inputs - replace with actual addresses for analysis
    inputs = {
        'wallet_address': '0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0', 
        'networks': 'ethereum,polygon,bnb chain'
    }
    
    print("\n## Starting Onchain AI Agent Analysis")
    print("------------------------------------------")
    print(f"Analyzing wallet: {inputs['wallet_address']}")
    print(f"Networks: {inputs['networks']}")
    print("------------------------------------------\n")
    
    try:
        # Execute the crew with our inputs
        result = OnchainAgentCrew().crew().kickoff(inputs=inputs)
        
        # Display results
        print("\n## Analysis Complete")
        print("------------------------------------------")
        print("Intelligence report saved to: onchain_intelligence_report.md")
        print("------------------------------------------\n")
        
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise Exception(f"An error occurred while running the Onchain AI Agent crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        OnchainAgent().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        OnchainAgent().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }
    try:
        OnchainAgent().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

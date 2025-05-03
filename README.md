# Onchain AI Agent Streamlit Interface

This Streamlit application provides a user interface for the Onchain AI Agent system, enabling blockchain portfolio analysis across multiple networks.

## Features

- Blockchain wallet analysis across multiple networks
- Portfolio composition analysis
- Transaction pattern recognition
- Cross-chain investment opportunities
- Comprehensive intelligence reports

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Get required API keys:
   - [Zapper API](https://zapper.xyz) - For blockchain data access
   - [OpenRouter](https://openrouter.ai) - For LLM access

3. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

## Usage

1. Enter your API keys in the sidebar
2. Input a wallet address to analyze
3. Select blockchain networks to include
4. Click "Run Analysis" to start the process
5. View and download the generated report

## Project Structure

- `app.py` - Main Streamlit application
- `agent_bridge.py` - Bridge between UI and Onchain agent
- `output_handler.py` - Agent output handling for Streamlit
- `requirements.txt` - Project dependencies

## Dependencies

- streamlit
- crewai
- python-dotenv
- requests

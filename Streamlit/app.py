import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add the absolute path to the onchain_agent directory
onchain_agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "onchain_agent", "src")
sys.path.append(onchain_agent_path)

# Import after path is set
from onchain_agent.crew import OnchainAgentCrew

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Onchain AI Agent",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state variables
if "api_keys_set" not in st.session_state:
    st.session_state.api_keys_set = False

# Main header
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>🔍 Onchain AI Agent</h1>", unsafe_allow_html=True)

# Sidebar for API keys
with st.sidebar:
    st.title("Configuration")
    
    # API Keys
    with st.expander("API Keys", expanded=True):
        st.warning("API keys are stored in session memory only and are not saved.")
        
        zapper_api_key = st.text_input(
            "Zapper API Key",
            type="password",
            help="Required for blockchain data access"
        )
        
        openrouter_api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            help="Required for LLM access"
        )
        
        if zapper_api_key and openrouter_api_key:
            # Set environment variables
            os.environ["ZAPPER_API_KEY"] = zapper_api_key
            os.environ["OPENROUTER_API_KEY"] = openrouter_api_key
            st.session_state.api_keys_set = True
            st.success("API keys set successfully!")
        else:
            st.session_state.api_keys_set = False
    
    # About section
    with st.expander("About", expanded=False):
        st.markdown("""
        **Onchain AI Agent** analyzes blockchain wallet data across multiple networks to provide:
        
        - Portfolio composition analysis
        - Transaction pattern recognition
        - Cross-chain investment opportunities
        - Comprehensive intelligence reports
        
        ### Developer
        
        **Emmanuel Ezeokeke**
        
        Connect with me:
        - [LinkedIn](https://www.linkedin.com/in/emma-ezeokeke/)
        - [X / Twitter](https://x.com/Emarh_AI)
        - [YouTube](https://www.youtube.com/)
        
        Powered by [CrewAI](https://crewai.com) and [Zapper API](https://zapper.xyz).
        """)

# Main content
col1, col2 = st.columns([3, 1])

with col1:
    wallet_address = st.text_input(
        "Wallet Address",
        value="",
        placeholder="Enter an EVM-compatible wallet address",
        help="Enter any EVM-compatible wallet address"
    )

with col2:
    networks = st.multiselect(
        "Networks",
        options=["ethereum", "polygon", "optimism", "arbitrum", "base", "avalanche", "bnb-smart-chain"],
        default=["ethereum", "polygon", "base"],
        help="Select blockchain networks to analyze"
    )

# Convert networks to comma-separated string
networks_str = ",".join(networks)

# Run analysis button
run_button = st.button("🚀 Run Analysis", type="primary", disabled=not st.session_state.api_keys_set)

# Check if API keys are set before running
if run_button:
    if not st.session_state.api_keys_set:
        st.error("Please set your API keys in the sidebar first.")
    else:
        # Prepare inputs for the crew
        inputs = {
            'wallet_address': wallet_address,
            'networks': networks_str
        }
        
        # Create output directories
        Path("outputs").mkdir(exist_ok=True, parents=True)
        Path("memory").mkdir(exist_ok=True, parents=True)
        
        # Run the analysis with progress tracking
        with st.status("Running blockchain analysis...", expanded=True) as status:
            try:
                # Display initial information
                st.write(f"Analyzing wallet: {wallet_address}")
                st.write(f"Networks: {networks_str}")
                
                # Initialize and run the crew
                crew = OnchainAgentCrew()
                result = crew.crew().kickoff(inputs=inputs)
                
                # Update status when complete
                status.update(label="✅ Analysis complete!", state="complete", expanded=False)
            except Exception as e:
                status.update(label=f"❌ Error: {str(e)}", state="error")
                st.error(f"An error occurred: {str(e)}")
                st.stop()
        
        # Display results
        try:
            # Read the generated report
            with open("outputs/onchain_intelligence_report.md", "r") as file:
                report_content = file.read()
            
            # Display the report
            st.markdown(report_content)
            
            # Download button1
            st.download_button(
                label="📥 Download Report",
                data=report_content,
                file_name="onchain_intelligence_report.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"Error loading results: {str(e)}")

# Footer
st.markdown("---")
st.caption("Made with ❤️ using CrewAI and Streamlit")

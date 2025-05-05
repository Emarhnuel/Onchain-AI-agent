from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv
from crewai.memory import LongTermMemory
from crewai import LLM
from crewai.memory.storage import ltm_sqlite_storage
from pathlib import Path
     
# Import all Zapper API tools
from onchain_agent.tools import (
    PortfolioTool,
    TransactionHistoryTool,
    TokenPriceTool,
    TransactionDetailsTool,
    AppTransactionsTool,
    SearchTool
)

# Load environment variables for API keys
import os
load_dotenv()  # This loads the variables from .env
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

llm = LLM(
    model="openrouter/google/gemini-2.5-flash-preview:thinking",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0.5,
    max_tokens=50000
) 

# llm2 = LLM(
#     model="openrouter/deepseek/deepseek-r1",
#     base_url="https://openrouter.ai/api/v1",
#     api_key=OPENROUTER_API_KEY,
#     temperature=0.5,
#     max_tokens=30000
# )


@CrewBase
class OnchainAgentCrew():
    """
    Onchain AI Agent Crew for blockchain data analysis.
    
    This Crew orchestrates specialized agents to analyze on-chain data including portfolio
    composition, transaction patterns, and cross-chain opportunities using Zapper API.
    """

    # Configuration files for agents and tasks
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
 

    def __init__(self):
        """Initialize the Audience Analysis Crew."""
        super().__init__()
        
        # Set up output directories
        Path("outputs").mkdir(exist_ok=True, parents=True)
        Path("memory").mkdir(exist_ok=True, parents=True) 


    # Portfolio Intelligence Analyst Agent
    @agent
    def portfolio_intelligence_analyst(self) -> Agent:
        """Portfolio Intelligence Analyst agent with portfolio analysis tools."""
        return Agent( 
            config=self.agents_config['portfolio_intelligence_analyst'],
            llm=llm,
            verbose=True,
            tools=[
                PortfolioTool(),
                TokenPriceTool(),
                SearchTool()
            ],
            max_rpm=40,
            max_iter=10
        )
 
    # Transaction Pattern Recognition Specialist Agent
    @agent
    def transaction_pattern_specialist(self) -> Agent:
        """Transaction Pattern Recognition Specialist agent with transaction analysis tools."""
        return Agent(
            config=self.agents_config['transaction_pattern_specialist'],
            verbose=True,
            tools=[
                TransactionHistoryTool(),
                TransactionDetailsTool(),
                AppTransactionsTool(),
                SearchTool() 
            ],
            max_rpm=20,
            max_iter=10,
            llm=llm
        )

    # Cross-Chain Investment Strategist Agent
    @agent
    def cross_chain_investment_strategist(self) -> Agent:
        """Cross-Chain Investment Strategist agent with cross-chain analysis tools."""
        return Agent(
            config=self.agents_config['cross_chain_investment_strategist'],
            verbose=True,
            llm=llm,
            tools=[
                PortfolioTool(),
                SearchTool()
            ],
            max_rpm=20,
            max_iter=10  
        )
        
    # Strategic Intelligence Synthesizer Agent
    @agent
    def strategic_intelligence_synthesizer(self) -> Agent:
        """Strategic Intelligence Synthesizer agent with comprehensive analysis tools."""
        return Agent(
            config=self.agents_config['strategic_intelligence_synthesizer'],
            verbose=True,
            llm=llm,
            max_rpm=20,
            max_iter=6
        )


    # Portfolio Analysis Task
    @task
    def portfolio_analysis(self) -> Task:
        """Task for analyzing portfolio composition and performance."""
        return Task(
            config=self.tasks_config['portfolio_analysis'],
            agent=self.portfolio_intelligence_analyst()
        )

    # Transaction Pattern Analysis Task
    @task
    def transaction_pattern_analysis(self) -> Task:
        """Task for analyzing transaction patterns and behaviors."""
        return Task(
            config=self.tasks_config['transaction_pattern_analysis'],
            agent=self.transaction_pattern_specialist(),
            context=[
                self.portfolio_analysis()
            ]  # Use portfolio analysis as context
        )



    # Investment Opportunity Identification Task
    @task
    def investment_opportunity_identification(self) -> Task:
        """Task for identifying investment opportunities across chains."""
        return Task(
            config=self.tasks_config['investment_opportunity_identification'],
            agent=self.cross_chain_investment_strategist(),
            context=[
                self.portfolio_analysis(),
                self.transaction_pattern_analysis()
            ]  # Use all previous analyses as context
        )

    # Comprehensive Intelligence Report Task
    @task
    def comprehensive_intelligence_report(self) -> Task:
        """Task for creating a comprehensive intelligence report synthesizing all analyses."""
        return Task(
            config=self.tasks_config['comprehensive_intelligence_report'],
            agent=self.strategic_intelligence_synthesizer(),
            context=[
                self.portfolio_analysis(),
                self.transaction_pattern_analysis(),
                self.investment_opportunity_identification()
            ],  # Use all previous tasks as context
            output_file= "outputs/onchain_intelligence_report.md"  # Save final report to file
        )

    # Crew Definition with Sequential Process
    @crew
    def crew(self) -> Crew:
        """Creates the OnchainAgent crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, 
            verbose=True,
            long_term_memory=LongTermMemory(
                storage=ltm_sqlite_storage.LTMSQLiteStorage(
                    db_path="memory/onchain_memory.db"
                )
            )
            
        )



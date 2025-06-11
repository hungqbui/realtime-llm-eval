from dotenv import load_dotenv
from langchain_core.tools import Tool, tool
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import PydanticToolsParser
load_dotenv("../../.env")

from langchain_community.utilities import GoogleSerperAPIWrapper

# TODO: Had to rewrote a lot of the ChatLlamaCpp class from LangChain, and use a non-merge PR for llama-cpp-python to use "auto" tool choice. Reminder to keep the libraries up to date. 

try:
    
    # Initialize the LLM model with the specified parameters.
    llm = ChatLlamaCpp(
        model_path="/data/qbui2/proj/dev/realtime-llm-eval/server/models/saves/medgemma-27b-text-it-Q6_K.gguf",
        n_batch=512,
        verbose=False,
        n_ctx=50000, # Set up to 131072
        n_gpu_layers=-1,
        max_tokens=2048,
    )

    # Search tool using SerpAPI
    search = GoogleSerperAPIWrapper()
    tools = [
        Tool(name="search_answer", func=search.run, description="Use when you need search the internet to answer questions about current events."),
    ]

    # Bind the tools to the LLM and create a ReAct agent.
    llm_with_tools = llm.bind_tools(tools, tool_choice="auto") # This is not possible without the custom LlamaCpp class
    agent = create_react_agent(llm_with_tools, tools=tools)

except Exception as e:
    print(f"Error loading LLM model: {e}")
    llm = None

def llm_answer(question, history=None, context=None):
    """
    Function to get an answer from the LLM model based on the question and optional history.
    Args:
        question (str): The question to ask the LLM.
        history (list, optional): A list of previous messages in the conversation.
        context (str, optional): Additional context for the LLM.
    Returns:
        Generator: A generator that yields messages from the LLM.
    """


    formatted_history = [

        HumanMessage(content=h["text"]) if h.get("type") == "User" else
        AIMessage(content=h["text"])

        for h in history
    ] if history else []
        
    out = agent.stream({"messages": [
            *(history),
            HumanMessage(content=question)
        ]},
        stream_mode="messages" # For token level streaming (not possible without custom _stream method in LlamaCpp class)
    )

    return out
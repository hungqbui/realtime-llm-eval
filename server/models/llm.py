from dotenv import load_dotenv
from langchain_core.tools import Tool, tool
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv("/data/qbui2/proj/dev/realtime-llm-eval/.env")

from langchain_community.utilities import GoogleSerperAPIWrapper

# TODO: Had to rewrote a lot of the ChatLlamaCpp class from LangChain, and use an unmerged PR for llama-cpp-python to use "auto" tool choice. Reminder to keep the libraries up to date. 

try:
    
    # Initialize the LLM model with the specified parameters.
    # llm = ChatLlamaCpp(
    #     model_path="/data/qbui2/proj/dev/realtime-llm-eval/server/models/saves/gemma-3-4b-it-UD-Q8_K_XL.gguf",
    #     n_batch=512,
    #     verbose=False,
    #     n_ctx=131072, # Set up to 131072
    #     n_gpu_layers=-1,
    #     max_tokens=1024,
    #     temperature=0.1,
    #     n_threads=4,
    # )

    from llama_cpp import Llama
    llm = Llama(
        model_path="/data/qbui2/proj/dev/realtime-llm-eval/server/models/saves/medgemma-4b-it-UD-Q8_K_XL.gguf",
        n_batch=512,
        verbose=False,
        n_ctx=131072,  # Set up to 131072
        n_gpu_layers=-1,
        max_tokens=1024,
        temperature=0.1,
        n_threads=4,
    )

    # Search tool using SerpAPI
    # search = GoogleSerperAPIWrapper()
    # tools = [
    #     Tool(name="search_answer", func=search.run, description="Useful when you need search the internet to answer questions about latest information."),
    # ]

    # # Bind the tools to the LLM and create a ReAct agent.
    # llm_with_tools = llm.bind_tools(tools, tool_choice="auto") # This is not possible without the custom LlamaCpp class
    # agent = create_react_agent(llm_with_tools, tools=tools)

except Exception as e:
    print(f"Error loading LLM model: {e}")
    llm = None

def llm_answer(question, history=None, context=None, emotions=None, patient_info=None):
    """
    Function to get an answer from the LLM model based on the question and optional history.
    Args:
        question (str): The question to ask the LLM.
        history (list, optional): A list of previous messages in the conversation.
        context (str, optional): Additional context for the LLM.
        emotions (dict, optional): List of detected emotions at different timestamps.
        patient_info (dict, optional): Information about the patient.
    Returns:
        Generator: A generator that yields messages from the LLM.
    """

    emotion_context = f"The user across the dialogue has shown the following emotions: \n"
    if emotions:
        for emotion in emotions:
            emotion_context += f"At time {emotion['time']} combination of:\n"
            for e in emotion["emotions"]:
                emotion_context += f" {e["name"]} with probability {e['score']:.2f}.\n"

        emotion_context += "Combine this information with the timeline of the transcription to add details about possible underlying problems with the patient report.\n"


    formatted_history = [

        {
            "role": "assistant" if h["type"] == "AI" else "user",
            "content": h["content"],
        }

        for h in history
    ] if history else []

    messages = [
        {
            "role": "system",
            "content": f"""The AI is a medical assistant that works alongside a clinical professional to provide medical recommendations based on the patient's symptoms and history. The AI is not a doctor, but it can provide useful information and recommendations to help the doctor make a decision while providing reasoning on why it thinks that's the way to go based on the context, while keeping it concise for concise questions.\n{f'Conversation Context: \n\"{context}\"\n' if context else 'There is no transcription provided.'}{ f"\n{emotion_context if emotions else ''} "}{("\nPatient Background: " + str(patient_info)) if patient_info else ""}\nHere comes the back and forth dialogue.""",
        },
        *(formatted_history),
        {
            "role":"user",
            "content": question
        }
    ]

    out = llm.create_chat_completion(
        messages=messages,
        stream=True
        # stream_mode="messages", # For token level streaming (not possible without custom _stream method in LlamaCpp class)
    )

    return out

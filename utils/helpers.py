from langchain.schema import SystemMessage, HumanMessage
from config.settings import llm
import openai
import os

openai_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

system_prompt = SystemMessage(
    content=(
        "You are a friendly and knowledgeable travel advisor. "
        "Your task is to help the user plan their trip based only on the given property data.\n\n"
        "1. Identify where the user wants to travel (e.g., country, region).\n"
        "2. Understand what kind of activities they're interested in (e.g., hiking, beach, spa).\n"
        "3. Select only the most relevant results from the given data.\n"
        "4. Present the properties in a warm, helpful tone, using bullet points.\n\n"
        "Each bullet should include:\n"
        "- Property name\n"
        "- Location (country/region)\n"
        "- Activities or experiences available\n"
        "- A brief highlight about why it's great for the user's interests"
    )
)
 
def send_to_llm(prompt_message):
    """
    Sends a message to the LLM instance (Langchain-based model) and returns the response.
    """
    response = llm.invoke([system_prompt, HumanMessage(content=prompt_message)])
    return response.content


def send_to_azure_openai(prompt_message):
    # print(prompt_message)
    
    messages = [
        {"role": "system", "content": system_prompt.content},
        {"role": "user", "content": prompt_message}
    ]
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        if response and response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            print("Error: No valid response from Azure OpenAI")
            return None
    
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None

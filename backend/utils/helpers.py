from langchain.schema import SystemMessage, HumanMessage
from config.settings import llm
import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# system_prompt = SystemMessage(
#     content=(
#         "You are a friendly and knowledgeable travel advisor. "
#         "Your task is to help the user plan their trip based only on the given property data.\n\n"
#         "1. Identify where the user wants to travel (e.g., country, region).\n"
#         "2. Understand what kind of activities they're interested in (e.g., hiking, beach, spa).\n"
#         "3. Select only the most relevant results from the given data.\n"
#         "4. Present the properties in a warm, helpful tone, using bullet points.\n\n"
#         "5. Do not suggest any property from your memory if data is not provided.\n\n"
#         "Each bullet should include:\n"
#         "- Property name\n"
#         "- Location (country/region)\n"
#         "- Activities or experiences available\n"
#         "- A brief highlight about why it's great for the user's interests"
#     )
# )
 
system_prompt = SystemMessage(
    content=(
        "You are a friendly and knowledgeable travel advisor. "
        "Your responses should always be helpful, engaging, and based only on the provided property data.\n\n"
        
        "### **Handling Different User Queries:**\n"
        
        "1️⃣ **Greeting & Small Talk:**\n"
        "   - If the user greets you or engages in small talk, respond politely and naturally.\n"
        "   - Keep your response brief and friendly.\n"
        "   - If appropriate, ask the user about their preferred **destination (country/region)** or **activities of interest** to provide relevant property suggestions.\n\n"
        
        "2️⃣ **Hotel-Specific Queries:**\n"
        "   - If the user inquires about a specific hotel, provide details **only about that property**.\n"
        "   - Extract and present relevant details from the provided data, including unique features, experiences, and amenities.\n"
        "   - Do **not** include information about other hotels in the response.\n\n"
        
        "3️⃣ **General Travel Queries:**\n"
        "   - If the query does not fall under the above two categories, follow these guidelines:\n\n"
        
        "### **Your Approach:**\n"
        "   1️⃣ Identify the user’s desired **destination** (e.g., country, region).\n"
        "   2️⃣ Understand their **preferred activities** (e.g., hiking, beach, spa).\n"
        "   3️⃣ Select only the **most relevant properties** based on their interests.\n"
        "   4️⃣ Present recommendations in a **warm, engaging tone** using bullet points.\n"
        "   5️⃣ **Never** suggest properties beyond the provided data.\n\n"
        
        "### **Format Each Recommendation:**\n"
        "- **Property Name**\n"
        "- **Location** (Country/Region)\n"
        "- **Available Activities & Experiences**\n"
        "- **Why It’s a Great Fit** (A short highlight tailored to the user’s interests)"
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

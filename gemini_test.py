from google import genai
import os

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

response = client.interactions.create(
    model="gemini-3.6-flash",
    input="Say hello to the Quantumaze AI Engine."
)

print(response.output_text)
# test_llm.py — tạo file này ở root, chạy thử
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Say hello"
)
print(response.text)

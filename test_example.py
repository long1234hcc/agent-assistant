# test_llm.py — tạo file này ở root, chạy thử
# from google import genai
# import os
# from dotenv import load_dotenv

# load_dotenv()

# client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
# response = client.models.generate_content(
#     model="gemini-3-flash-preview",
#     contents="Say hello"
# )
# print(response.text)
import os
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

load_dotenv()

api = TodoistAPI(os.environ.get("TODOIST_API_KEY"))

INBOX_ID = "6g86j8F6cGWp3RF5"

tasks = [task for page in api.get_tasks() for task in page]
inbox_tasks = [t for t in tasks if t.project_id == INBOX_ID]

for task in inbox_tasks:
    print(f"- {task.content} | Due: {task.due}")

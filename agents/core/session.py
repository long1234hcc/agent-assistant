import os
import json
import datetime


class Session:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.file_path = os.path.join(
            os.path.dirname(__file__),   # agents/core/
            "..", "..",                  # lên root
            "workspace", "sessions",
            f"{session_id}.jsonl"
        )
        # Normalize path
        self.file_path = os.path.normpath(self.file_path)

        # Tạo folder nếu chưa có
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, entry: dict):
        """
        Append 1 entry vào file JSONL.
        Mỗi dòng là 1 JSON object độc lập.

        Args:
            entry: dict chứa thông tin cần lưu
                   ví dụ: {"user_input": "...", "answer": "...", "tools_used": [...]}
        """
        entry["timestamp"] = datetime.datetime.now().isoformat()
        entry["session_id"] = self.session_id

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def load(self) -> list[dict]:
        """
        Load toàn bộ entries từ file JSONL.
        Trả về list rỗng nếu file chưa tồn tại.
        """
        if not os.path.exists(self.file_path):
            return []

        entries = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # bỏ qua dòng bị corrupt

        return entries

    def clear(self):
        """
        Xóa toàn bộ session — xóa file JSONL.
        """
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

def parse(response) -> dict:
    """
    Parse Gemini response object → dict chuẩn để Agent xử lý.

    Returns:
        {
            "type": "tool_call",
            "tool_name": "search_github_repositories",
            "tool_args": {"query": "AI agent", "days": 7}
        }
        hoặc:
        {
            "type": "text",
            "content": "Đây là kết quả..."
        }
    """
    # Case 1 — LLM muốn gọi tool
    if response.function_calls:
        fc = response.function_calls[0]
        return {
            "type":      "tool_call",
            "tool_name": fc.name,
            "tool_args": dict(fc.args)
        }

    # Case 2 — LLM trả lời thẳng
    if response.text:
        return {
            "type":    "text",
            "content": response.text
        }

    # Case 3 — Không có gì cả (safety filter hoặc lỗi)
    return {
        "type":    "text",
        "content": "[No response from LLM]"
    }

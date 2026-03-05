from agents.core.history import History
from agents.core.session import Session
from agents.prompts.builder import PromptBuilder
from agents.models.base import BaseLLM
from agents.mcp.registry import Registry
from agents.core.parser import parse


class Agent:
    def __init__(self, session: Session, history: History, prompt_builder: PromptBuilder, llm: BaseLLM, tools_registry: Registry, prompt_params: dict = None):
        self.session = session
        self.history = history
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.tools_registry = tools_registry
        self.prompt_params = prompt_params or {}

    def run(self, user_input: str):

        system_prompt = self.prompt_builder.build_system_prompt(
            **self.prompt_params)
        self.history.add(user_input, role="user")

        max_iterations = 5
        iteration = 0
        tools_used = []

        while iteration < max_iterations:
            iteration += 1
            print(f"\n[Iteration {iteration}] Calling LLM...")

            # Call test tool used to debug tool passing
            tools = list(self.tools_registry.all().values())
            print(f"[Agent] Tools being passed: {[t.__name__ for t in tools]}")

            response = self.llm.generate_response(
                messages=self.history.get_history(),
                system_prompt=system_prompt,
                tools=list(self.tools_registry.all().values())
            )
            print(f"[Agent] Got response ✓")
            parsed = parse(response)
            print(f"[Agent] Response type: {parsed['type']}")

            if parsed["type"] == "tool_call":
                tool_name = parsed["tool_name"]
                tool_args = parsed["tool_args"]
                print(
                    f"[Agent] Calling tool: {tool_name} with args: {tool_args}")

                tool_func = self.tools_registry.get(tool_name)
                tool_result = tool_func(**tool_args)
                print(
                    f"[Agent] Tool result preview: {str(tool_result)[:200]}...")

                self.history.add(str(tool_result), role="user")
                tools_used.append({"tool": tool_name, "args": tool_args})

            elif parsed["type"] == "text":
                print(f"[Agent] Final answer received.")
                self.history.add(parsed["content"], role="model")
                self.session.save({
                    "user_input": user_input,
                    "answer":     parsed["content"],
                    "tools_used": tools_used,
                })
                return parsed["content"]

        print("[Agent] Max iterations reached.")
        return None

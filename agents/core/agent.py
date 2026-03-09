from agents.core.history import History
from agents.core.session import Session
from agents.prompts.builder import PromptBuilder
from agents.models.base import BaseLLM
from agents.mcp.registry import Registry
from agents.core.parser import parse
from google.genai import types


class Agent:
    def __init__(
        self,
        session: Session,
        history: History,
        prompt_builder: PromptBuilder,
        llm: BaseLLM,
        tools_registry: Registry,
        prompt_params: dict = None,
        enable_reflection: bool = True,
    ):
        self.session           = session
        self.history           = history
        self.prompt_builder    = prompt_builder
        self.llm               = llm
        self.tools_registry    = tools_registry
        self.prompt_params     = prompt_params or {}
        self.enable_reflection = enable_reflection

    # ── Self Reflection ───────────────────────────────────────────────────────

    def self_reflect(self, user_input: str, answer: str) -> str:
        """
        Gọi LLM riêng để đánh giá answer — chỉ chạy 1 lần duy nhất.

        Returns:
            "GOOD"            → answer đủ tốt
            "NEEDS: <reason>" → cần bổ sung
        """
        reflection_prompt = f"""User asked: {user_input}
Agent answered: {answer}

ONLY check:
- Is the answer relevant to what was asked?
- Is the answer coherent and well-structured?

DO NOT check data accuracy.
DO NOT suggest calling tools or fetching more data.
DO NOT verify repository names or external sources.

Reply GOOD or NEEDS: <reason about relevance/structure only>"""

        response = self.llm.client.models.generate_content(
            model=self.llm.model_name,
            config=types.GenerateContentConfig(
                system_instruction="You are a strict answer reviewer. Reply only GOOD or NEEDS: <reason>.",
            ),
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=reflection_prompt)]
                )
            ]
        )

        return response.text.strip() if response.text else "GOOD"

    # ── Main Run Loop ─────────────────────────────────────────────────────────

    def run(self, user_input: str):

        system_prompt = self.prompt_builder.build_system_prompt(**self.prompt_params)
        self.history.add(user_input, role="user")

        max_iterations = 7
        iteration      = 0
        tools_used     = []
        reflected      = False  # ← flag: chỉ reflect 1 lần duy nhất

        while iteration < max_iterations:
            iteration += 1
            print(f"\n[Iteration {iteration}] Calling LLM...")

            tools = list(self.tools_registry.all().values())
            print(f"[Agent] Tools being passed: {[t.__name__ for t in tools]}")

            response = self.llm.generate_response(
                messages=self.history.get_history(),
                system_prompt=system_prompt,
                tools=tools
            )
            print(f"[Agent] Got response ✓")
            parsed = parse(response)
            print(f"[Agent] Response type: {parsed['type']}")

            # ── Tool call ─────────────────────────────────────────────────────
            if parsed["type"] == "tool_call":
                tool_name = parsed["tool_name"]
                tool_args = parsed["tool_args"]
                print(f"[Agent] Calling tool: {tool_name} with args: {tool_args}")

                tool_func   = self.tools_registry.get(tool_name)
                tool_result = tool_func(**tool_args)
                print(f"[Agent] Tool result preview: {str(tool_result)[:200]}...")

                self.history.add(str(tool_result), role="user")
                tools_used.append({"tool": tool_name, "args": tool_args})

            # ── Text answer ───────────────────────────────────────────────────
            elif parsed["type"] == "text":
                answer = parsed["content"]

                if self.enable_reflection and not reflected:
                    # Lần đầu có text → reflect
                    print(f"[Agent] Running self-reflection...")
                    reflection = self.self_reflect(user_input, answer)
                    reflected  = True  # ← đánh dấu ngay, không reflect lần 2
                    print(f"[Agent] Reflection: {reflection}")

                    if reflection.startswith("GOOD"):
                        # Đủ tốt → save và return
                        print(f"[Agent] Reflection passed ✓")
                        self.history.add(answer, role="model")
                        self.session.save({
                            "user_input": user_input,
                            "answer":     answer,
                            "tools_used": tools_used,
                        })
                        return answer

                    else:
                        # Chưa đủ → inject feedback, loop tiếp
                        feedback = reflection.replace("NEEDS:", "").strip()
                        print(f"[Agent] Needs improvement: {feedback}")
                        self.history.add(
                            f"[Self Review] Your answer is incomplete. {feedback}. Please improve.",
                            role="user"
                        )
                        # Không return — iteration tiếp theo LLM sẽ bổ sung

                else:
                    # reflected=True (đã reflect rồi) hoặc enable_reflection=False
                    # → return luôn, không reflect lần 2
                    print(f"[Agent] Final answer received.")
                    self.history.add(answer, role="model")
                    self.session.save({
                        "user_input": user_input,
                        "answer":     answer,
                        "tools_used": tools_used,
                    })
                    return answer

        print("[Agent] Max iterations reached.")
        return None
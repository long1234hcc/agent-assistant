from agents.orchestration.orchestrator import create_orchestrator

orchestrator = create_orchestrator()

if __name__ == "__main__":
    user_input = input("Nhập câu hỏi: ")
    result = orchestrator.run(user_input)
    print(f"\n{result}")

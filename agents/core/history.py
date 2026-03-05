class History:
    def __init__(self, max_length=100):
        self.max_length = max_length
        self.history = []

    def add(self, content, role="user"):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_length:
            self.history.pop(0)

    def get_history(self):

        return self.history

    def clear(self):
        self.history = []

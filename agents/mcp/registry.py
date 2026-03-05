class Registry:
    def __init__(self):
        self._registry = {}

    def register(self, name, obj):
        self._registry[name] = obj

    def get(self, name):
        if name not in self._registry:
            raise ValueError(
                f"Object with name '{name}' not found in registry.")
        return self._registry.get(name)

    def all(self):
        return self._registry

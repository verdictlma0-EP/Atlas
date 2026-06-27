class Tool:
    def __init__(self, name, func, schema):
        self.name = name
        self.func = func
        self.schema = schema  # {"args": {...}, "preconditions": [], "postconditions": []}

class Event():
    def __init__(self):
        self.canceled = False

    def preventDefault(self):
        self.canceled = True

class KeyEvent(Event):
    def __init__(self, key):
        super().__init__()

        self.key = key
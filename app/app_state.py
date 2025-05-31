class AppState:
    def __init__(self):
        self.theme = "minecraft"
        self.variant = "light"
        self.user = {"name": None, "dob": None}
        self.volume = 70
        self.alarm = {}
        self.schedule = {}
        self.sensor_data = {}
        self.notifications = []
        self.media_files = []

app_state = AppState()
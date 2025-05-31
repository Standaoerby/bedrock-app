import subprocess

class AudioService:
    def __init__(self, device="default"):
        self.device = device

    def play(self, filepath):
        subprocess.Popen(["aplay", "-D", f"plughw:{self.device}", filepath])

    def stop(self):
        subprocess.call(["pkill", "aplay"])

    def set_volume(self, percent):
        subprocess.call(["amixer", "-c", self.device, "sset", "Speaker", f"{percent}%"])

audio_service = AudioService(device="1,0")
import os
import sounddevice as sd
import soundfile as sf
import threading

class Recorder:
    def __init__(self):
        self.recording = False
        self.stream = None
        self.file = None

    def start(self, filename="recording.wav"):
        if self.recording:
            return

        self.file = sf.SoundFile(
            os.path.join(os.path.dirname(__file__), filename),
            mode="w",
            samplerate=24000,
            channels=1,
        )

        def callback(indata, frames, time, status):
            if status:
                print(status)

            self.file.write(indata)

        self.stream = sd.InputStream(
            samplerate=24000,
            channels=1,
            callback=callback,
        )

        self.stream.start()
        self.recording = True

    def stop(self):
        if not self.recording:
            return

        self.stream.stop()
        self.stream.close()
        self.file.close()

        self.recording = False
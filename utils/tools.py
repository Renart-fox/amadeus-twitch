import librosa

def get_audio_duration(file_path):
    return librosa.get_duration(filename=file_path) + 1
import librosa
import subprocess
import json

# Uses librosa to get the duration of an audio file, and adds 1 second to it to account for any potential discrepancies.
def get_audio_duration(file_path):
    return librosa.get_duration(filename=file_path) + 1


# Uses ffprobe to get the duration of a video file. This is done by running a subprocess that calls ffprobe with the appropriate arguments, and then parsing the output to extract the duration.
def get_video_duration(video_path):
    result = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{video_path}"',
            shell=True).decode()
    fields = json.loads(result)['streams'][0]
    duration = fields['duration']
    return float(duration)
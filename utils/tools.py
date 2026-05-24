import librosa
import subprocess
import json
import edge_tts
from googletrans import Translator

# Uses librosa to get the duration of an audio file, and adds 1 second to it to account for any potential discrepancies.
def get_audio_duration(file_path):
    return librosa.get_duration(path=file_path) + 1


# Uses ffprobe to get the duration of a video file. This is done by running a subprocess that calls ffprobe with the appropriate arguments, and then parsing the output to extract the duration.
def get_video_duration(video_path):
    result = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{video_path}"',
            shell=True).decode()
    fields = json.loads(result)['streams'][0]
    duration = fields['duration']
    return float(duration)


def apply_reverb_ffmpeg(input_path, output_path):
    command = [
        'ffmpeg',
        '-y',
        '-hide_banner',
        '-i', input_path,
        '-af', 'aecho=0.8:0.88:20:0.3',
        output_path,
        '-loglevel', 'error'
    ]
    subprocess.run(command, check=True)


async def translate_text(text):
    async with Translator() as translator:
        result = await translator.translate(text, dest='ja')
        return result.text


async def create_text_to_speech_audio(text) -> float:
    #translation = await translate_text(text)
    communicate = edge_tts.Communicate(text, voice="fr-CH-ArianeNeural", pitch="+11Hz", rate="+33%")
    await communicate.save("F:\\Twitch\\Amadeus\\assets\\sounds\\output.mp3")
    apply_reverb_ffmpeg("F:\\Twitch\\Amadeus\\assets\\sounds\\output.mp3", "F:\\Twitch\\Amadeus\\assets\\sounds\\output_reverb.mp3")
    return get_audio_duration("F:\\Twitch\\Amadeus\\assets\\sounds\\output_reverb.mp3")
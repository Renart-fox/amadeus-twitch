from typing import Literal, List, Dict, Any
import yaml
import asyncio
import os

from obs.obs_manager import OBS_Manager
from utils import tools


class Handler():
    def __init__(self, config: str) -> None:
        self.config = yaml.safe_load(config)
        self.obs_manager = OBS_Manager().get_instance()

    async def process(self, kwargs: dict = {}):
        print(f'Processing with kwargs: {kwargs}')
        print(f'Config: {self.config}')
        current_scene_name = self.obs_manager.get_current_scene_name()
        running_args : Dict[str, Any] = {}
        video_counter = 0
        audio_counter = 0

        for idx, action in enumerate(self.config):
            action_name = list(action.keys())[0]
            match action_name:
                case 'play_video':
                    video_path = action[action_name].get('video', '')
                    volume = action[action_name].get('volume', -10.0)
                    monitoring_type = action[action_name].get('monitoring_type', 'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT')
                    loop = action[action_name].get('loop', False)
                    duration = tools.get_video_duration(video_path)

                    # Create video input
                    video_input_id, video_scene_item_id = self.obs_manager.create_input(
                        scene_name=current_scene_name,
                        input_kind="ffmpeg_source",
                        input_settings={
                            "local_file": video_path,
                            "is_local_file": True,
                            "looping": loop
                        }
                    )
                    
                    # Set video volume
                    self.obs_manager.set_volume(
                        input_id=video_input_id,
                        volume=volume
                    )

                    # Set video monitoring type
                    self.obs_manager.set_input_audio_monitor_type(
                        input_id=video_input_id,
                        monitor_type=monitoring_type
                    )

                    running_args[f'video_{video_counter}'] = video_scene_item_id
                    running_args[f'video_{video_counter}_duration'] = duration
                    video_counter += 1

                case 'play_sound':
                    audio_path = action[action_name].get('sound', '')
                    volume = action[action_name].get('volume', -10.0)
                    monitoring_type = action[action_name].get('monitoring_type', 'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT')
                    duration = tools.get_audio_duration(audio_path)

                    # Create audio input
                    audio_input_id, audio_scene_item_id = self.obs_manager.create_input(
                        scene_name=current_scene_name,
                        input_kind="ffmpeg_source",
                        input_settings={
                            "local_file": audio_path,
                            "is_local_file": True,
                            "looping": False
                        }
                    )

                    # Set audio volume
                    self.obs_manager.set_volume(
                        input_id=audio_input_id,
                        volume=volume
                    )

                    # Set audio monitoring type
                    self.obs_manager.set_input_audio_monitor_type(
                        input_id=audio_input_id,
                        monitor_type=monitoring_type
                    )

                    running_args[f'audio_{audio_counter}'] = audio_scene_item_id
                    running_args[f'audio_{audio_counter}_duration'] = duration
                    audio_counter += 1

                case 'wait':
                    duration_val = action[action_name].get('duration', '0')
                    duration = str(duration_val).format_map(running_args)
                    print(f'Waiting for {duration} seconds...')
                    await asyncio.sleep(eval(duration))
                    print('Done waiting.')

                case 'remove_input':
                    item = action[action_name].get('item', '')
                    item_id = int(item.format_map(running_args))
                    print(item_id)
                    res = self.obs_manager.remove_input(
                        current_scene_name,
                        item_id
                    )
                    print(res)
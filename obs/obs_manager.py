from typing import Dict
from uuid import uuid4
import os

from config.amadeus_config import Amadeus_Config

from obswebsocket import obsws, requests

class OBS_Manager():

    def get_instance(self, host: str = "", port: int = -1, password: str = ""):
        if not OBS_Manager._obs_manager:
             OBS_Manager._obs_manager = OBS_Manager._OBS_Manager(host, port, password)
        return OBS_Manager._obs_manager

    class _OBS_Manager():

        def __init__(self, host: str, port: int, password: str) -> None:
            self.host = host
            self.port = port
            self.password = password

            self.ws = obsws(self.host, self.port, self.password)
            self.ws.connect()


        def get_current_scene_name(self):
            current_scene = self.ws.call(requests.GetSceneList())
            return current_scene.datain['currentProgramSceneName']
        

        def get_scene_item_list(self, scene_name: str):
            response = self.ws.call(requests.GetSceneItemList(
                sceneName=scene_name
                ))
            return response.datain['sceneItems']
        

        def get_scene_item_transform(self, scene_name: str, scene_item_id: str):
            res = self.ws.call(requests.GetSceneItemTransform(
                sceneItemId=int(scene_item_id),
                sceneName=scene_name
            ))
            return res.datain['sceneItemTransform']
        

        def set_scene_item_transform(self, scene_name: str, scene_item_id: str, transform: dict):
            res = self.ws.call(requests.SetSceneItemTransform(
                sceneItemId=int(scene_item_id),
                sceneName=scene_name,
                sceneItemTransform=transform
            ))
            return res
        
        
        def create_input(self, scene_name: str, input_kind: str, input_settings: Dict):
            input_name = str(uuid4())
            res = self.ws.call(requests.CreateInput(
                sceneName=scene_name,
                inputName=input_name,
                inputKind=input_kind,
                inputSettings=input_settings
            ))
            return (res.datain['inputUuid'], res.datain['sceneItemId'])
        

        def set_volume(self, input_id: str, volume: float):
            res = self.ws.call(requests.SetInputVolume(
                inputUuid=input_id,
                inputVolumeDb=volume
            ))
            return res
        

        def set_input_audio_monitor_type(self, input_id: str, monitor_type: str):
            res = self.ws.call(requests.SetInputAudioMonitorType(
                inputUuid=input_id,
                monitorType=monitor_type
            ))
            return res


        def remove_input(self, scene_name: str, item_id: int):
            res = self.ws.call(requests.RemoveSceneItem(
                sceneName=scene_name,
                sceneItemId=item_id
            ))
            return res
        
        def apply_green_screen(self, source_uuid: str):
            res = self.ws.call(requests.GetSourceFilterDefaultSettings(
                filterKind='chroma_key_filter_v2'
            ))
            default = res.datain['defaultFilterSettings']

            res = self.ws.call(requests.CreateSourceFilter(
                sourceUuid=source_uuid,
                filterName='chroma_key_filter_v2',
                filterKind='chroma_key_filter_v2',
                filterSettings=default
            ))

        def set_blend_mode(self, item_id: str, blend_mode: str = 'OBS_BLEND_MULTIPLY'):
            res = self.ws.call(requests.SetSceneItemBlendMode(
                sceneItemId=int(item_id),
                sceneItemBlendMode=blend_mode
            ))
            return res
        
        
        def screenshot_scene(self, scene_name: str):
            path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'screen.png')
            self.ws.call(requests.SaveSourceScreenshot(
                sourceName=scene_name,
                imageFormat='png',
                imageFilePath=path
            ))
            return path
    
    _obs_manager : _OBS_Manager = None
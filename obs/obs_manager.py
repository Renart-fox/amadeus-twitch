from typing import Dict
from uuid import uuid4

from config.amadeus_config import Amadeus_Config

from obswebsocket import obsws, requests

class OBS_Manager():

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
            sceneItemId=float(scene_item_id),
            sceneName=scene_name
        ))
        return res.datain['sceneItemTransform']
    

    def set_scene_item_transform(self, scene_name: str, scene_item_id: str, transform: dict):
        res = self.ws.call(requests.SetSceneItemTransform(
            sceneItemId=float(scene_item_id),
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
        return input_name
    

    def set_volume(self, input_name: str, volume: float):
        res = self.ws.call(requests.SetInputVolume(
            inputName=input_name,
            inputVolumeDb=volume
        ))
        return res
    

    def set_input_audio_monitor_type(self, input_name: str, monitor_type: str):
        res = self.ws.call(requests.SetInputAudioMonitorType(
            inputName=input_name,
            monitorType=monitor_type
        ))
        return res


    def remove_input(self, input_name: str):
        res = self.ws.call(requests.RemoveInput(
            inputName=input_name
        ))
        return res
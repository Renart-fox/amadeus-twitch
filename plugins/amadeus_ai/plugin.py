import os, subprocess, asyncio, re, datetime

from uuid import uuid4

from typing import Dict, List

from models.amadeus_plugin import AmadeusPlugin
from models.decorators import on_follow, on_load, on_chat_message, on_custom_message, CustomMessage, on_stream_start, on_stream_update
from models.globals import set_global, get_global
from models.signal_manager import emit_signal
from config.amadeus_config import Amadeus_Config
from twitchAPI.twitch import Twitch
from twitchAPI.chat import ChatCommand, Chat

from pydantic_ai import Agent
from pydantic import dataclasses

from queue import Queue
from threading import Thread

from TTS.api import TTS

from .data import amadeus_ai_personnality
from .amadeus_db import Amadeus_DB
from .recorder import Recorder
from utils import tools

from obs.obs_manager import OBS_Manager

import chromadb


PLUGIN_NAME = "amadeus_ai"


obs_manager = OBS_Manager()
amadeus_voice_queue = Queue()
talk_to_amadeus_queue = Queue()

@dataclasses.dataclass
class Amadeus_FindUser():
    users_sumarries: List[str]


@dataclasses.dataclass
class Amadeus_Output():
    amadeus_response: str
    amadeus_facts_to_remember: List[str]


@dataclasses.dataclass
class Validator_Output():
    message_is_appropriate: bool


class Amadeus(AmadeusPlugin):
    

    plugin_name = PLUGIN_NAME
    amadeus_agent : Agent
    recorder : Recorder = Recorder()

    tts = TTS(
        "tts_models/multilingual/multi-dataset/xtts_v2"
    ).to("cuda")


    def __init__(self) -> None:
        super().__init__()

        self.config_parser.set(self.plugin_name, 'anthropic_secret', '')

        self.write_config(overwrite=False)
        self.read_config()

        if self.active:
            from faster_whisper import WhisperModel
            self.whisper_model = WhisperModel("base")
            self.db = Amadeus_DB(self.plugin_name, self.config_parser)
            self.chroma_client = chromadb.PersistentClient()
            self.chroma_client.get_or_create_collection(name='amadeus_ai')

            amadeus_voice_thread = Thread(target=self.manage_amadeus_voice, daemon=True)
            talk_to_amadeus_thread = Thread(target=self.talk_to_amadeus, daemon=True)

            amadeus_voice_thread.start()
            talk_to_amadeus_thread.start()

            app = get_global('fastapi_app')

            @app.get('/amadeus_ai/record')
            async def record_endpoint():
                print('Start recording')
                self.recorder.start()
            
            @app.get('/amadeus_ai/stop_record')
            async def stop_record_endpoint():
                print('Stop recording')
                self.recorder.stop()
                talk_to_amadeus_queue.put('recording.wav')


    def talk_to_amadeus(self):
        while True:
            message = talk_to_amadeus_queue.get()
            if message is not None:
                segments, info = self.whisper_model.transcribe(os.path.join(os.path.dirname(__file__), 'recording.wav'), language='fr')

                text = "".join(segment.text for segment in segments)
                print(text)

                print(f"[{PLUGIN_NAME}] Amadeus plugin is processing the message with the agent...")

                ### Récupération des événements de stream
                session_facts = '\n'.join(self.session_facts)
                collection = self.chroma_client.get_or_create_collection(name='amadeus_ai')
                memory_from_rag = 'Rien pour le moment.'

                query_result = collection.query(query_texts=[text], n_results=5)
                print(query_result)
                if len(query_result['documents'][0]) > 0:
                    memory_from_rag = '\n===\n'.join(f'{a} {b}' for a, b in zip(query_result['documents'][0], query_result['metadatas'][0]))

                message_to_amadeus = f'# Voici ce que tu as en mémoire:\n{memory_from_rag}\n# Nouveau message vocal de Miel ; ce dernier étant du speech to text, il peut comporter des erreurs\n#Règle pour les "facts to remember" : ne jamais retenir de données biométriques telles que l\'âge, l\'appartenance ethnique, la race, le sexe ou les handicaps\n# Contenu du message\n{text}'

                print(message_to_amadeus)

                ### Message d'Amadeus
                result = self.amadeus_agent.run_sync(
                    [
                        f'# Voici ce que tu as en mémoire:\n{memory_from_rag}\n# Nouveau message vocal de Miel ; ce dernier étant du speech to text, il peut comporter des erreurs\n#Règle pour les "facts to remember" : \n# Contenu du message\n{text}'
                    ],
                    message_history=self.message_history,
                    output_type=Amadeus_Output
                )

                print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_response}")
                print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_facts_to_remember}")

                for possible_memory in result.output.amadeus_facts_to_remember:
                    query_result = collection.query(query_texts=[possible_memory], n_results=5)
                    nearest_saved_memories = '- None'
                    if len(query_result['documents'][0]) > 0:
                        nearest_saved_memories = '\n===\n'.join(f'{a} {b}' for a, b in zip(query_result['documents'][0], query_result['metadatas'][0]))
                    validator_result = self.validator_agent.run_sync(
                        f'Requested memory to store : {possible_memory}\nList of nearest already saved memories:\n{nearest_saved_memories}',
                        output_type=Validator_Output)

                    print(f"[{PLUGIN_NAME}] Value : {possible_memory} / Validator output : {validator_result.output.message_is_appropriate}")

                    if validator_result.output.message_is_appropriate == True:
                        ### Mise à jour des événements de stream
                        self.message_history += result.new_messages()
                        self.session_facts.append(possible_memory)
                        self.chroma_client.get_or_create_collection(name='amadeus_ai').add(
                            ids=[str(uuid4())],
                            documents=[possible_memory],
                            metadatas=[{
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                            }]
                        )

                ### Reformattage du texte afin de pouvoir être contenu dans 1 à N messages Twitch
                text = result.output.amadeus_response

                amadeus_voice_queue.put(text)


    def manage_amadeus_voice(self):
        while True:
            message = amadeus_voice_queue.get()

            if message is not None:
                emotions_messages = []
                current_emotion = 'neutral'

                parts = re.split(r'(\[[^\]]+\])', message)
                for part in parts:
                    if not part or part == '':
                        continue
                    if re.fullmatch(r'\[[^\]]+\]', part):
                        current_emotion = part[1:-1]
                    else:
                        emotions_messages.append((current_emotion, part))
                
                audios = []
                for emotion, text in emotions_messages:
                    audio_file_path = asyncio.run(self.create_audio(text, len(audios)))
                    audios.append(audio_file_path)

                for audio_file_path, e_m in zip(audios, emotions_messages):
                    obs_manager.set_input_settings(
                        '5e8660b5-1f39-4019-81a8-26db09c2bc22',
                        {
                            'text': e_m[1].replace('.', '.\n'),
                        }
                    )
                    asyncio.run(self.play_audio(audio_file_path))
                    os.remove(audio_file_path)

                obs_manager.set_input_settings(
                        '5e8660b5-1f39-4019-81a8-26db09c2bc22',
                        {
                            'text': '',
                        }
                    )


    async def retrieve_amadeus_data(self, cmd: ChatCommand):
        summary = self.db.get_user_summary_by_id(cmd.user.id)
        twitch_bot: Twitch = get_global('twitch_bot')
        await twitch_bot.send_whisper(from_user_id='1232194164', to_user_id=str(cmd.user.id), message=summary)


    @on_load
    async def on_load(self) -> None:
        await super().on_load()

        from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
        from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
        from pydantic_ai.providers.anthropic import AnthropicProvider

        from pydantic_ai.models.ollama import OllamaModel
        from pydantic_ai.providers.ollama import OllamaProvider

        self.amadeus_config = Amadeus_Config()
        

        self.model_provider = AnthropicProvider(api_key=self.config_parser[self.plugin_name]['anthropic_secret'])
        self.model = AnthropicModel('claude-haiku-4-5-20251001',
                            provider=self.model_provider,
                            settings=AnthropicModelSettings(
                                anthropic_cache_instructions='1h',
                                anthropic_cache_tool_definitions='1h'
                            ))
        
        """ 
        self.model_provider = OllamaProvider(
            base_url='http://localhost:11434/v1',
        )
        self.model = OllamaModel('qwen3.5:9b-q4_K_M', provider=self.model_provider)
        """
        self.amadeus_agent = Agent(model=self.model, system_prompt=amadeus_ai_personnality(), tools=[duckduckgo_search_tool()])
        self.validator_agent = Agent(model=self.model, system_prompt="""
        Return:

message_is_appropriate: true
or
message_is_appropriate: false

Reject if the memory contains:

- age
- date of birth
- location
- address
- health
- disability
- ethnicity
- religion
- political opinions
- sexual orientation
- gender identity
- biometric information
- financial information
- legal information
- passwords
- contact information

Accept:

- Twitch usernames
- game preferences
- favorite characters
- projects
- current stream events
- jokes
- recurring interests
- goals
- software preferences
- programming projects

When uncertain, reject.

Only keep information that is likely to remain useful weeks or months later.

Do not store in memory something that is already saved (set message_is_appropriate: false otherwise).
Do not store temporary events.
        """)
        self.message_history = []
        self.session_facts = []

        print(f"[{PLUGIN_NAME}] Amadeus plugin is now ready to use")


    @on_stream_start
    async def on_stream_start(self):
        twitch_bot: Twitch = get_global('twitch_bot') # type: ignore
        user = get_global('main_user')
        channel_info = await twitch_bot.get_channel_information(broadcaster_id=user.id) # type: ignore
        game_name = channel_info[0].game_name
        stream_title = channel_info[0].title

        result = await self.amadeus_agent.run(
            f'Amadeus, le live commence. La catégorie / le jeu est {game_name}. Miel indique que le titre de son stream est le suivant : "{stream_title}". A toi désormais d\'accueilir le chat !'
        )
        self.message_history += result.new_messages()
        self.session_facts.append(result.output)
        await self.send_twitch_message(result.output)


    @on_stream_update
    async def on_stream_update(self):
        twitch_bot: Twitch = get_global('twitch_bot') # type: ignore
        user = get_global('main_user')
        channel_info = await twitch_bot.get_channel_information(broadcaster_id=user.id) # type: ignore
        game_name = channel_info[0].game_name
        stream_title = channel_info[0].title

        result = await self.amadeus_agent.run(
            f'Amadeus, Miel vient de changer le titre/la catégorie du stream. La catégorie / le jeu est désormais {game_name}. Miel indique que le titre de son stream est le suivant : "{stream_title}".'
        )
        self.message_history += result.new_messages()
        self.session_facts.append(result.output)
        await self.send_twitch_message(result.output)
        

    @on_chat_message
    async def on_chat_message(self, message):
        await super().on_chat_message(message)
        print(f"[{PLUGIN_NAME}] Amadeus plugin received chat message: {message}")

        if self.amadeus_config.twitch_bot_username.lower() in message.user.name.lower():
            return
        
        user_summary = self.db.get_user_summary_by_id(message.user.id)

        # Regarde si le message mentionne Amadeus
        if f'@{self.amadeus_config.twitch_bot_username.lower()}' in message.text.lower():
            print(f"[{PLUGIN_NAME}] Amadeus plugin is processing the message with the agent...")

            ### Récupération des événements de stream
            session_facts = '\n'.join(self.session_facts)

            ### Message d'Amadeus
            result = await self.amadeus_agent.run(
                [
                    f'# Evenements du chat\n{session_facts}\n# Nouveau message de {message.user.name}\n# Ce que je sais de cet·te viewer\n{user_summary}#Règle pour les "facts to remember" : ne jamais retenir de données biométriques telles que l\'âge, l\'appartenance ethnique, la race, le sexe ou les handicaps\n# Contenu du message\n{message.text}'
                ],
                message_history=self.message_history,
                output_type=Amadeus_Output
            )

            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_response}")
            print(f"[{PLUGIN_NAME}] Amadeus plugin got the following result from the agent: {result.output.amadeus_facts_to_remember}")

            validator_result = await self.validator_agent.run(
                result.output.amadeus_facts_to_remember
            , output_type=Validator_Output)

            print(f"[{PLUGIN_NAME}] Validator output : {validator_result.output.message_is_appropriate} / Reason: {validator_result.output.reason}")

            if validator_result.output.message_is_appropriate == True:
                ### Mise à jour des événements de stream
                self.message_history += result.new_messages()
                self.session_facts.append(result.output.amadeus_facts_to_remember)

            ### Reformattage du texte afin de pouvoir être contenu dans 1 à N messages Twitch
            text = result.output.amadeus_response

            amadeus_voice_queue.put(text)

            """
            max_len = 485
            
            chunks = []
            while text:
                if len(text) <= max_len:
                    chunks.append(text)
                    break
                
                split_at = text.rfind(' ', max_len - 50, max_len)
                if split_at == -1 or split_at < max_len - 50:
                    split_at = max_len
                
                chunks.append(text[:split_at].strip())
                text = text[split_at:].strip()
            
            for chunk in chunks:
                if chunk:
                    await message.reply(chunk)

            await self.play_audio(text)


            # Crée un résumé des événements de stream pour ne pas surcharger le contexte
            if len(self.session_facts) > 30:
                res = await self.amadeus_agent.run(
                    f"Voici la liste des événements du stream. Crée un résumé du contenu en quelques phrases parmi ce qui semble être le plus important :\n{session_facts}"
                )
                self.session_facts = []
                self.session_facts.append(res.output)
                
                print(f'[{self.plugin_name}] Amadeus has condensed stream events into : {res.output}')
            """


    @on_custom_message
    async def on_custom_message(self, message: CustomMessage):
        if message.from_plugin == 'streamlabs_charity':
            if message.data['type'] == 'new_donation':
                don_info = message.data
                res = await self.amadeus_agent.run(
                    f"Amadeus, nous venons de recevoir un don de {don_info['donation_amount_formatted']} de la part de {don_info['donation_from']} pour l'événement caritatif soutenant l'association des Petits Princes pour aider les enfants atteints de maladies graves à réaliser leurs rêves. Je te laisse remercier chaleureusement la personne, tout comme je le fais actuellement !"
                )
                text = res.output
                
                if don_info['donation_from_twitchname'] != '':
                    text = f"@{don_info['donation_from_twitchname']} " + text

                await self.send_twitch_message(text)

                c = CustomMessage(self.plugin_name, {'type':'get_session_donations'}, 'streamlabs_charity')
                await emit_signal('on_custom_message', c)
            if message.data['type'] == 'session_donations':
                session_donations = message.data['donations']
                res = await self.amadeus_agent.run(
                    f"Amadeus, voici la liste de tous les dons faits au cours de cette session de stream pour l'événement caritatif soutenant l'association des Petits Princes pour aider les enfants atteints de maladies graves à réaliser leurs rêves:\n{session_donations}\nJe te laisse remercier chaleureusement toutes ces personnes, avec la plus grande tendresse et joie possible."
                )
                text = res.output

                await self.send_twitch_message(text)
                self.play_audio(text)
        
        elif message.from_plugin == 'amadeus_discord':
            if message.data['type'] == 'discord_message':
                res = await self.amadeus_agent.run(
                    message.data['content']
                )
                text = res.output
                
                c = CustomMessage(self.plugin_name,
                                  {
                                      'type': 'amadeus_discord_message',
                                      'message': message.data['message'],
                                      'content': text
                                  },
                                  'amadeus_discord')
                await emit_signal('on_custom_message', c)

    
    async def send_twitch_message(self, text):
        chat: Chat = get_global('chat')

        max_len = 485
            
        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            
            split_at = text.rfind(' ', max_len - 50, max_len)
            if split_at == -1 or split_at < max_len - 50:
                split_at = max_len
            
            chunks.append(text[:split_at].strip())
            text = text[split_at:].strip()
        
        for chunk in chunks:
            if chunk:
                await chat.send_message(self.amadeus_config.target_channel, chunk)


    async def create_audio(self, text, index):
        self.tts.tts_to_file(
            text=text,
            speaker_wav=os.path.join(os.path.dirname(__file__), 'speaker.wav'),
            language="fr",
            file_path=os.path.join(os.path.dirname(__file__), f'response_audio_{index}.wav')
        )

        uuid = str(uuid4())

        cmd = [
            "ffmpeg",
            "-y",  # overwrite output file
            "-i", os.path.join(os.path.dirname(__file__), f'response_audio_{index}.wav'),
            "-filter:a", f"atempo=1.2",
            os.path.join(os.path.dirname(__file__), f'{uuid}.wav')
        ]

        subprocess.run(cmd)

        os.remove(os.path.join(os.path.dirname(__file__), f'response_audio_{index}.wav'))

        return os.path.join(os.path.dirname(__file__), f'{uuid}.wav')


    async def play_audio(self, file_path):

        duration = tools.get_audio_duration(file_path)

        current_scene_name = obs_manager.get_current_scene_name()

        obs_manager.set_input_settings(
            'c0e0f0c8-086b-45ed-b812-dfa013432d1d',
            {
                'local_file': file_path,
                'is_local_file': True
            }
        )

        await asyncio.sleep(duration)


exported_class = Amadeus
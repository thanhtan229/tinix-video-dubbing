import logging
import mimetypes
import random
import struct
from dataclasses import dataclass, field
from typing import Union, Dict, List

from google import genai
from google.genai.errors import APIError, ClientError
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.config import params, logger, settings
from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file
import time
import wave
import base64


def is_daily_quota_error(message: str) -> bool:
    text = (message or '').lower()
    return 'perday' in text or 'per day' in text


@dataclass(repr=False)
class GEMINITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT+(APIError,)), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):return
        role = data_item['role']
        try:
            self.generate_tts_segment(data_item['text'], role, params.get('gemini_ttsmodel',''),
                                      data_item['filename'] + '.wav')
        except APIError as e:
            raise StopTask(e.message)
        self.convert_to_wav(data_item['filename'] + '.wav', data_item['filename'])

    @staticmethod
    def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)


    def generate_tts_segment(self,text, voice, model, file_name):
        api_keys=params.get('gemini_key', '').strip().split(',')
        api_key = api_keys[random.randint(0,len(api_keys)-1)]
        client = genai.Client(
            api_key=api_key,
            http_options = types.HttpOptions(
                client_args={'proxy': self.proxy_str},
                async_client_args={'proxy': self.proxy_str},
            ) if self.proxy_str else None
        )


        # Free tier allows a few TTS requests per minute; wait and retry on 429 instead of failing the task.
        for attempt in range(1, 6):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                            )
                        ),
                    ),
                )
                break
            except ClientError as e:
                # Daily quota will not reset within a retry window; fail at once so requests are not wasted.
                if getattr(e, 'code', None) != 429 or attempt == 5 or is_daily_quota_error(str(e)):
                    raise
                logger.warning(f'[gemini-tts] rate limited, retry {attempt} in 21s')
                time.sleep(21)
        pcm = response.candidates[0].content.parts[0].inline_data.data
        self.wave_file(file_name, pcm)


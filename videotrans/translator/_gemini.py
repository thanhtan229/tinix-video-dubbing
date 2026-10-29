import logging
import random
import re,httpx
from dataclasses import dataclass, field
from typing import List, Union
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from videotrans.configure.excepts import NO_RETRY_EXCEPT, TranslateSrtError, StopTask
from videotrans.configure.config import tr,settings,params,logger
from videotrans.translator._base import BaseTrans
from google import genai
from google.genai import types,errors


@dataclass(repr=False)
class Gemini(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.ainame='gemini'
        self.model_name = params.get("gemini_model",'gemini-flash-latest')
        self.prompt=self._set_context()


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO),after=after_log(logger, logging.INFO))
    def _item_task(self, data: str) -> str:
        if self._exit(): return
        text = data
        client=None
        try:
            model = params.get("gemini_model","gemini-flash-latest")
            thinking_config = None
            if model.startswith('gemini-3') or model.startswith('gemini-4') or model.startswith('gemini-flash'):
                thinking_config = types.ThinkingConfig(thinking_level="high")
            
            api_keys=params.get('gemini_key', '').strip().split(',')
            api_key = api_keys[random.randint(0,len(api_keys)-1)]
            client = genai.Client(
                api_key=api_key,
                http_options = types.HttpOptions(
                    timeout=30_000 if self.is_test else None,
                    client_args={'proxy': self.proxy_str} if self.proxy_str else None,
                    async_client_args={'proxy': self.proxy_str} if self.proxy_str else None,
                ) if (self.proxy_str or self.is_test) else None
            )
            
            message=self.prompt.replace('{batch_input}', f'{text}')
            logger.debug(f'{message=}')
            result = client.models.generate_content(
                model=model,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction="You are a top-tier Subtitle Translation Engine.",
                    thinking_config=thinking_config,
                ),
            )
            if not result or not result.text:
                logger.warning(f'[gemini]请求失败')
                raise TranslateSrtError(f"[Gemini]result is empty")

            match = re.search(r'<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)',
                              re.sub(r'<think>(.*?)</think>', '', result.text, flags=re.I | re.S), re.S | re.I)
            if match:
                return match.group(1)
            raise TranslateSrtError(f"Gemini result is emtpy")
        except httpx.ConnectTimeout as e:
            raise StopTask(f' {tr("Unable to connect to remote API","Gemini AI")}\n{e}') from e
        except httpx.TimeoutException as e:
            if self.is_test:
                raise StopTask(f'{tr("Gemini test request timed out after 30 seconds")}\n{e}') from e
            raise
        except errors.APIError as e:
            logger.warning(f'{e=}')
            if e.code in [400,403,404,429,500]:
                raise StopTask(e.message)
            raise TranslateSrtError(e.message)
        finally:
            if client:
                client.close()
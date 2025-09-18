import aiohttp
import asyncio
import configparser

config = configparser.ConfigParser()
config.read('config.ini', encoding="utf-8")

api_key = config.get("captcha", "captcha_api_key")
captcha_solver_engine = config.get("captcha", "captcha_solver_engine")


class CaptchaSolver:

    def __init__(self, engine: str):
        self.engine = engine.lower()

    @staticmethod
    async def _create_task(session, url, payload):
        async with session.post(url, json=payload) as resp:
            data = await resp.json(content_type=None)
            if "errorId" in data and data["errorId"] != 0:
                print("[CaptchaSolver] Erro ao criar tarefa:", data)
                return None
            return data

    @staticmethod
    async def _get_result(session, url, task_id, api_key, attempts=30, delay=2):
        payload = {"clientKey": api_key, "taskId": task_id}
        for _ in range(attempts):
            await asyncio.sleep(delay)
            async with session.post(url, json=payload) as resp:
                result = await resp.json(content_type=None)
                if result.get("status") == "ready":
                    solution = (
                        result["solution"].get("gRecaptchaResponse")
                        or result["solution"].get("token")
                        or result["solution"].get("text")
                    )
                    return solution
                elif "errorId" in result and result["errorId"] != 0:
                    print("[CaptchaSolver] Erro ao obter resultado:", result)
                    return None
        print("[CaptchaSolver] Timeout: resultado não pronto após várias tentativas.")
        return None

    async def solve(self, captcha_type: str, website_url: str, website_key: str) -> str | None:
        captcha_type = captcha_type.lower()

        if self.engine == "anticaptcha":
            create_url = "https://api.anti-captcha.com/createTask"
            result_url = "https://api.anti-captcha.com/getTaskResult"
            type_map = {
                "recaptcha": "NoCaptchaTaskProxyless",
                "hcaptcha": "HCaptchaTaskProxyless",
                "turnstile": "TurnstileTaskProxyless"
            }
        elif self.engine == "capsolver":
            create_url = "https://api.capsolver.com/createTask"
            result_url = "https://api.capsolver.com/getTaskResult"
            type_map = {
                "recaptcha": "ReCaptchaV2TaskProxyLess",
                "hcaptcha": "HCaptchaTaskProxyLess",
                "turnstile": "AntiTurnstileTaskProxyLess"
            }
        elif self.engine == "capmonster":
            create_url = "https://api.capmonster.cloud/createTask"
            result_url = "https://api.capmonster.cloud/getTaskResult"
            type_map = {
                "recaptcha": "NoCaptchaTaskProxyless",
                "hcaptcha": "HCaptchaTaskProxyless",
                "turnstile": "TurnstileTaskProxyless"
            }
        else:
            raise ValueError(
                f"Engine desconhecido: '{self.engine}'. Suportado: anticaptcha, capsolver, capmonster"
            )

        task_type = type_map.get(captcha_type)
        if not task_type:
            raise ValueError("Tipo de captcha inválido. Use recaptcha, hcaptcha ou turnstile.")

        payload = {
            "clientKey": api_key,
            "task": {
                "type": task_type,
                "websiteURL": website_url,
                "websiteKey": website_key
            }
        }
        if self.engine == "anticaptcha":
            payload["softId"] = 0
        elif self.engine == "capsolver":
            payload["task"]["metadata"] = {"action": "login"}

        async with aiohttp.ClientSession() as session:
            response = await self._create_task(session, create_url, payload)
            if not response:
                return None

            task_id = response.get("taskId")
            if not task_id:
                print("[CaptchaSolver] Nenhum taskId retornado:", response)
                return None

            result = await self._get_result(session, result_url, task_id, api_key)
            if not result:
                print("[CaptchaSolver] Falha ao obter token.")
            return result


async def resolve_captcha(captcha_type, url, site_key):
    solver = CaptchaSolver(captcha_solver_engine)
    print(f"[CaptchaSolver] Usando engine '{captcha_solver_engine}' para {captcha_type}")

    token = await solver.solve(
        captcha_type=captcha_type,
        website_url=url,
        website_key=site_key
    )

    if token:
        print("[CaptchaSolver] Token gerado com sucesso.")
    else:
        print("Erro: token do captcha não foi resolvido.")

    return token


async def hcaptcha_solver(url, site_key):
    return await resolve_captcha(
        "hcaptcha", url, site_key
    )


async def recaptcha_solver(url, site_key):
    return await resolve_captcha(
        "recaptcha", url, site_key
    )


async def turnstile_solver(url, site_key):
    return await resolve_captcha(
        "turnstile", url, site_key
    )

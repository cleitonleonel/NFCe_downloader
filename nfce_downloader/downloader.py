import re
import json
import requests
from nfce_downloader.services.captcha_solver import recaptcha_solver
from nfce_downloader.utils.requests_pfx_adapter import get, post

default_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
              "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "DNT": "1",
    "Host": "dfe-portal.svrs.rs.gov.br",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/140.0.0.0 Safari/537.36",
    "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Linux\""
}


def get_homepage(
        url: str,
        pfx_path: str = None,
        pfx_password: str = None
) -> 'requests.Response':
    headers = default_headers.copy()
    headers.update({
        "Sec-Fetch-Site": "none"
    })

    response = get(
        f"{url}/NFCESSL/DownloadXMLDFe",
        headers=headers,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        verify=True
    )
    return response


async def download_xml(
        url: str,
        nfce_key: str,
        site_key: str,
        pfx_path: str = None,
        pfx_password: str = None,
        ambiente: str = "1"
):
    headers = default_headers.copy()
    headers.update({
        "Content-Length": "1784",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": url,
        "Referer": f"{url}/NFCESSL/DownloadXMLDFe",
        "Sec-Fetch-Site": "same-origin"
    })
    url_download = f"{url}/NfceSSL/DownloadXmlDfe"

    recaptcha = await recaptcha_solver(
        url=url_download,
        site_key=site_key
    )

    data = {
        "sistema": "Nfce",
        "OrigemSite": "0",
        "Ambiente": ambiente,
        "ChaveAcessoDfe": nfce_key,
        "g-recaptcha-response": recaptcha,
        "recaptchaValor": recaptcha
    }

    response = post(
        url_download,
        data=data,
        headers=headers,
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        verify=True
    )

    if response.status_code != 200:
        print("Erro na requisição:", response.text)
        return

    json_data = {}
    matches = re.search(
        r"var stringJson\s*=\s*(\{.*?});",
        response.text,
        re.DOTALL
    )
    if matches:
        json_str = matches.group(1)
        json_data = json.loads(json_str)
    else:
        error_message = "Variável stringJson não encontrada"
        match = re.search(
            r'<h4 class="textoErro">(.*?)</h4>',
            response.text,
            re.DOTALL
        )
        if match:
            error_message = match.group(1)

        return error_message

    filename = f"{nfce_key}-teste.xml"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"{json_data.get('xml')}")

    print(f"✅ XML baixado e salvo em: {filename}")
    return json_data.get('xml')

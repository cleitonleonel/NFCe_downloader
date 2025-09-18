import time
import asyncio
import configparser
from nfce_downloader.downloader import get_homepage, download_xml

config = configparser.ConfigParser()
config.read('config.ini', encoding="utf-8")

cert_pfx_path = config.get("general", "cert_pfx_path")
cert_pfx_pass = config.get("general", "cert_pfx_pass")
production = config.getboolean("general", "production")
cnpj = config.get("general", "cnpj")
site_url = config.get("website", "site_url")
site_key = config.get("website", "site_key")


async def main(nfce_key: str):
    print(
        f"Baixando XML da NFC-e {nfce_key} do CNPJ {cnpj}"
    )
    home_page = get_homepage(
        site_url,
        pfx_path=cert_pfx_path,
        pfx_password=cert_pfx_pass
    )
    print(home_page.reason)

    new_xml = await download_xml(
        site_url,
        nfce_key,
        site_key=site_key,
        pfx_path=cert_pfx_path,
        pfx_password=cert_pfx_pass,
        ambiente="1" if production else "2"
    )
    print(new_xml)


if __name__ == "__main__":
    key = "32250933865985000177650010000403981893040009"
    time.sleep(2)
    asyncio.run(main(key))
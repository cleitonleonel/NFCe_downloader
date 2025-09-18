import requests
import ssl
import os
import secrets
import tempfile
import datetime

import cryptography.hazmat.backends
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.serialization.pkcs12
import cryptography.x509.oid

try:
    from ssl import PROTOCOL_TLS_CLIENT as default_ssl_protocol
except ImportError:
    from ssl import PROTOCOL_SSLv23 as default_ssl_protocol


def _check_cert_not_after(cert):
    cert_not_after = cert.not_valid_after_utc
    if cert_not_after < datetime.datetime.now(datetime.timezone.utc):
        raise ValueError(
            f"Client certificate expired: Not After: {cert_not_after:%Y-%m-%d %H:%M:%SZ}"
        )


def _create_sslcontext(
        pkcs12_data: bytes,
        pkcs12_password_bytes: bytes,
        ssl_protocol: int = None
):
    private_key, cert, ca_certs = cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates(
        pkcs12_data,
        pkcs12_password_bytes
    )
    _check_cert_not_after(cert)
    ssl_context = ssl.SSLContext(ssl_protocol)
    with tempfile.NamedTemporaryFile(delete=False) as c:
        try:
            tmp_pass = secrets.token_bytes(16)
            pk_buf = private_key.private_bytes(
                cryptography.hazmat.primitives.serialization.Encoding.PEM,
                cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
                cryptography.hazmat.primitives.serialization.BestAvailableEncryption(tmp_pass)
            )
            c.write(pk_buf)
            c.write(cert.public_bytes(
                cryptography.hazmat.primitives.serialization.Encoding.PEM)
            )
            if ca_certs:
                for ca_cert in ca_certs:
                    _check_cert_not_after(ca_cert)
                    c.write(ca_cert.public_bytes(
                        cryptography.hazmat.primitives.serialization.Encoding.PEM)
                    )
            c.flush()
            c.close()
            ssl_context.load_cert_chain(c.name, password=tmp_pass)
        finally:
            os.remove(c.name)
    return ssl_context


class Pkcs12Adapter(requests.adapters.HTTPAdapter):

    def __init__(
            self,
            *,
            pkcs12_filename: str = None,
            pkcs12_password: str = None,
            ssl_protocol: int = None,
            **kwargs
    ):
        if pkcs12_filename is None:
            raise ValueError('Argument "pkcs12_filename" is required')
        with open(pkcs12_filename, 'rb') as f:
            pkcs12_data = f.read()
        if isinstance(pkcs12_password, str):
            pkcs12_password_bytes = pkcs12_password.encode("utf-8")
        else:
            pkcs12_password_bytes = pkcs12_password
        if ssl_protocol is None:
            ssl_protocol = default_ssl_protocol
        self.ssl_context = _create_sslcontext(
            pkcs12_data,
            pkcs12_password_bytes,
            ssl_protocol
        )
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


def request(
        method: str,
        url: str,
        *,
        pkcs12_filename: str = None,
        pkcs12_password: str = None,
        **kwargs
) -> requests.Response:
    if pkcs12_filename is None:
        return requests.request(method, url, **kwargs)
    with requests.Session() as session:
        adapter = Pkcs12Adapter(
            pkcs12_filename=pkcs12_filename,
            pkcs12_password=pkcs12_password
        )
        session.mount("https://", adapter)
        return session.request(method, url, **kwargs)


def get(url: str, **kwargs) -> requests.Response:
    return request("get", url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return request("post", url, **kwargs)

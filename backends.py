import os
import requests
import logging

logger = logging.getLogger(__name__)

class VaultServerException(BaseException):
    pass

class VaultServer:
    def __init__(self, api_version: str = "v1"):
        self.base_url = os.getenv('VAULT_ADDR')
        self.token = os.getenv('VAULT_TOKEN')
        self.cacert = os.getenv('VAULT_CACERT', None)
        self.api_version = api_version
        self.session = requests.session()
        self.session.headers.update({"X-Vault-Token": self.token})

        if self.cacert is not None:
            self.session.verify = self.cacert

    def _request(self, url: str, method="GET"):
        full_url = f"{self.base_url}/{self.api_version}/{url.lstrip('/')}"
        logger.debug("Calling %s on %s", method, full_url)
        req = self.session.request(
            method=method,
            url=full_url
        )
        if not req.ok:
            logger.warning("Following request %s failed with %s %s", full_url, req.status_code, req.reason)

        # TODO: parse errors and warnings
        return req.json()['data']

    def mounts(self):
        # Remove system backends
        data = self._request('sys/mounts')
        return {x: {"type": v['type']} for x, v in data.items() if v['type'] not in ['system', 'cubbyhole', 'identity']}


    def list_secrets(self, mount, path="/"):
        data = self._request(f"{mount}/metadata/{path.lstrip('/')}", method="LIST")
        return data['keys']

    def get_secret(self, mount, path):
        return self._request(f"{mount}/data/{path}")['data']

import os
import requests
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import InitVar, dataclass, field

import requests
import requests.adapters
from textual import log

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
            logger.warning("Following request %s failed with %s %s", 
                           full_url, req.status_code, req.reason)

        # TODO: parse errors and warnings
        return req.json()['data']

    def mounts(self):
        # Remove system backends
        data = self._request('sys/mounts')
        return {x: {"type": v['type']} for x, v in data.items() 
                if v['type'] not in ['system', 'cubbyhole', 'identity']}


    def list_secrets(self, mount, path="/"):
        data = self._request(f"{mount}/metadata/{path.lstrip('/')}", method="LIST")
        return data['keys']

    def get_secret(self, mount, path):
        return self._request(f"{mount}/data/{path}")['data']


@dataclass
class NomadTask:
    expected: int
    running: int


@dataclass
class NomadJob:
    name: str
    status: str
    type: str
    tasks: dict[str, NomadTask] = field(default_factory=dict)
    deployment: str = "unknown"


@dataclass
class NomadCluster:
    url: str
    namespace: str | None
    client_cert: str | None
    client_key: str | None
    ca: str | None
    token: str | None
    jobs: dict[str, NomadJob] = field(default_factory=dict)
    session: InitVar[requests.Session | None] = None
    poolexecutor: ThreadPoolExecutor | None = None
    api_version: int = 1

    @classmethod
    def from_environ(cls):
        return cls(
            # Remove final slash if exists
            url=os.environ["NOMAD_ADDR"].rstrip("/"),
            namespace=os.getenv("NOMAD_NAMESPACE", "default"),
            client_cert=os.getenv("NOMAD_CLIENT_CERT", None),
            client_key=os.getenv("NOMAD_CLIENT_KEY", None),
            ca=os.getenv("NOMAD_CACERT", None),
            token=os.getenv("NOMAD_TOKEN", None),
            jobs=dict(),
        )

    def __post_init__(self, attr):
        # 10 is the requests.session pool
        self.poolexecutor = ThreadPoolExecutor(max_workers=32)

        self.session = requests.session()
        custom_adapter = requests.adapters.HTTPAdapter(pool_maxsize=32)
        self.session.mount('https://', custom_adapter)

        # Prepare request defaults
        if self.token:
            self.session.headers.update(
                {
                    "X-Nomad-Token": self.token,
                }
            )
        if self.ca:
            self.session.verify = self.ca
        if self.client_cert and self.client_key:
            self.session.cert = (self.client_cert, self.client_key)

    def _request(self, url: str, method: str = "get") -> requests.Response:
        started = time.monotonic()
        url = url.lstrip("/")
        url = f"{self.url}/v{self.api_version}/{url}?namespace={self.namespace}&stale=true"
        r = self.session.request(method, url)
        elapsed = time.monotonic() - started
        logger.debug("Requested url %s, time: %2.3fs", url, elapsed)
        return r

    def refresh_jobs(self):
        for job in self._request("/jobs").json():
            name = job["Name"]
            tasks = {}
            for task, tasks_details in sorted(job["JobSummary"]["Summary"].items()):
                tasks[task] = NomadTask(expected=0, running=tasks_details["Running"])
            self.jobs[name] = NomadJob(
                name=name,
                status=job["Status"],
                type=job["Type"],
                tasks=tasks,
                deployment="unknown",
            )
        self.refresh_deployments()
        self.refresh_scales()

    def refresh_scales(self):
        futures = {
            self.poolexecutor.submit(self._request, f"/job/{name}/scale"): name
            for name in self.jobs.keys()
        }
        for future in as_completed(futures):
            name = futures[future]
            for task, details in future.result().json()["TaskGroups"].items():
                self.jobs[name].tasks[task].expected = details["Desired"]
                self.jobs[name].tasks[task].running = details["Running"]

    def refresh_deployments(self):
        deployments = {k["JobID"]: k for k in self._request("/deployments").json()}
        for job in self.jobs.keys():
            try:
                self.jobs[job].deployment = deployments[job]["Status"]
            except KeyError:
                self.jobs[job].deployment = "unknown"

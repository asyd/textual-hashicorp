import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import InitVar, dataclass, field

import certifi
import requests
from textual import log

logger = logging.getLogger("nomad")


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
            client_key=os.getenv("NOMAD_CLIENT_CERT", None),
            ca=os.getenv("NOMAD_CACERT", None),
            token=os.getenv("NOMAD_TOKEN", None),
            jobs=dict(),
        )

    def __post_init__(self, attr):
        # 10 is the requests.session pool
        self.poolexecutor = ThreadPoolExecutor(max_workers=10)
        self.session = requests.session()
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

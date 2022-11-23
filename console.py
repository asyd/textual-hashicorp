#!/usr/bin/env python

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Header, Footer, DataTable
from dataclasses import dataclass, field
from rich.tree import Tree

import argparse
import certifi
import logging
import os
import requests


logger = logging.getLogger()


@dataclass
class NomadCluster:
  url: str
  namespace: str | None
  client_cert: str | None
  client_key: str | None
  ca: str | None
  token: str | None

  @classmethod
  def from_environ(cls):
    return cls(
      # Remove final slash if exists
      url = os.environ['NOMAD_ADDR'].rstrip('/'),
      namespace = os.getenv('NOMAD_NAMESPACE', None),
      client_cert = os.getenv('NOMAD_CLIENT_CERT', None),
      client_key = os.getenv('NOMAD_CLIENT_CERT', None),
      ca = os.getenv('NOMAD_CACERT', None),
      token= os.getenv('NOMAD_TOKEN', None)
    )

@dataclass
class NomadJob:
  name: str
  status: str
  type: str
  deployment: str = "unknown"
  subtasks: list[str] = field(default_factory=list)
  tasks_running: int = 0


def nomad_request(cluster: NomadCluster, url: str, method: str ="get", **kwargs) -> requests.Response:
  client_cert = (cluster.client_cert, cluster.client_key)
  truststore = certifi.where()
  if cluster.ca:
    truststore = cluster.ca

  r = requests.request(
    method,
    url, 
    cert=client_cert,
    verify=truststore,
    headers={'X-Nomad-Token': cluster.token} )

  logger.debug("Performed %s %s, got: %s", method, url, r.status_code)

  return r

def nomad_get_jobs(cluster: NomadCluster) -> list[NomadJob]:
  job_url = f"{cluster.url}/v1/jobs?"
  deployments_url = f"{cluster.url}/v1/deployments?"
  if cluster.namespace:
    job_url += f"namespace={cluster.namespace}&"
    deployments_url += f"namespace={cluster.namespace}&"

  jobs = []
  r = nomad_request(cluster, job_url)
  deployments = {k['JobID']: k for k in nomad_request(cluster, deployments_url).json()}

  for job in r.json():
    job_name = job['Name']
    try:
      last_deployment = deployments[job_name]['Status']
    except KeyError:
      last_deployment = 'unknown'
    jobs.append(
      NomadJob(
        name=job_name, 
        status=job['Status'], 
        type=job['Type'],
        deployment=last_deployment,
        subtasks=job['JobSummary']['Summary'].keys(),
        ))
  return jobs


class NomadJobsWidget(DataTable):

  jobs = reactive(list[NomadJob])

  def on_mount(self) -> None:
    self.cluster = NomadCluster.from_environ()
    self.update_jobs()
    self.add_column('Name')
    self.add_column('Status')
    self.add_column('Type')
    self.add_column('Last deployment')
    self.add_column('Subtasks')
    self.set_interval(1, self.update_jobs)

  def update_jobs(self) -> None:
    self.clear()
    for job in nomad_get_jobs(self.cluster):
      self.add_row(
        job.name,
        job.status,
        job.type,
        job.deployment,
        ", ".join(job.subtasks),
      )


class NomadMonitor(App):
  BINDINGS = [("q", "quit", "Quit")]

  def compose(self) -> ComposeResult:
    yield Header()
    yield Container(NomadJobsWidget(id='jobs'), DataTable(id='tasks'))
    yield Footer()


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--debug', action='store_true', default=False)

  logging.basicConfig()

  args = parser.parse_args()

  if args.debug:
    logger.setLevel(logging.DEBUG)
    # async def on_request_start(session, context, params):
    #   logging.getLogger('aiohttp.client').debug(f'Starting request <{params}>')

    # async def on_request_end(session, context, params):
    #     logging.getLogger('aiohttp.client').debug(f'Starting request <{params}>')

    # logging.root.setLevel(logging.DEBUG)
    # aiohttp_trace = aiohttp.TraceConfig()
    # aiohttp_trace.on_request_start.append(on_request_start)
    # aiohttp_trace.on_request_end.append(on_request_end)

  logger.debug("debug level test message")
  app = NomadMonitor()
  app.run()


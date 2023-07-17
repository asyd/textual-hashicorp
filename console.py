#!/usr/bin/env python

import argparse
import logging
import time

from rich.text import Text
from rich.tree import Tree
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import  DataTable, Footer, Header, Static

from nomad import NomadCluster

logger = logging.getLogger()


class NomadJobsWidget(DataTable):
    def on_mount(self) -> None:
        self.add_column("Name")
        self.add_column("Status")
        self.add_column("Type")
        self.add_column("Last deployment")
        self.add_column("Subtasks")
        self.update_jobs()
        self.set_interval(1, self.update_jobs)

    def update_jobs(self) -> None:
        self.clear()
        started = time.monotonic()
        self.app.cluster.refresh_jobs()
        elapsed = time.monotonic() - started
        try:
            self.screen.query_one("#stats").update(f"Last refresh took: {elapsed:2.3}s")
        except NoMatches:
            pass
        for name, job in self.app.cluster.jobs.items():
            tasks_height = len(job.tasks)
            tasks = Tree("Tasks", hide_root=True)
            for task_name, task in job.tasks.items():
                if job.deployment == "successful":
                    deployment = Text(job.deployment, style="green")
                elif job.deployment == "failed":
                    deployment = Text(job.deployment, style="red")
                else:
                    deployment = Text(job.deployment, style="dark_orange3")

                if job.type == "system":
                    tasks.add(Text(f"{task_name} ({task.running})"))
                else:
                    style = "green"
                    if task.running != task.expected:
                        style = "red"
                    tasks.add(
                        Text(
                            f"{task_name} ({task.running} / {task.expected})",
                            style=style,
                        )
                    )

            self.add_row(
                name,
                job.status,
                job.type,
                deployment,
                tasks,
                height=tasks_height,
            )


class Status(Widget):
    def compose(self) -> None:
        yield Static("Cluster URL:", id="cluster")
        yield Static("Last refresh took", id="stats")


class Filter(Screen):
    """Display filters"""

    DEFAULT_CSS = """
    Screen {
        margin: 4 8;
        layout: grid;
        content-align: center middle;
        grid-size: 2 2;
    }
    """

    BINDINGS = [("escape", "app.pop_screen", "close")]

    def compose(self) -> ComposeResult:
        yield Static("running")
        yield Static("dead")
        yield Footer()


class NomadMonitor(Screen):
    BINDINGS = [("f", "app.push_screen('filter')", "Filters")]

    def __init__(self):
        super().__init__()

    # Force focus on job list
    def on_mount(self) -> None:
        self.set_focus(self.query_one("#jobs"))
        self.query_one("#cluster").update(f"Nomad URL: {self.app.cluster.url}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            NomadJobsWidget(id="jobs"),
            Status(),
        )
        yield Footer()


class App(App):
    BINDINGS = [("q", "quit", "Quit")]
    CSS_PATH = "console.css"

    SCREENS = {
        "main": NomadMonitor,
        "filter": Filter,
    }

    def on_mount(self) -> None:
        self.capture_mouse(None)
        self.cluster: NomadCluster = NomadCluster.from_environ()
        self.push_screen("main")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--job-type")

    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig()

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("debug level test message")
    app = App()
    app.run()

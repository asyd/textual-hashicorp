#!/usr/bin/env python3

from textual import log
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, TabbedContent, Static, TabPane
from textual.widgets.tree import TreeNode
from textual.logging import TextualHandler

import requests
import os
import sys
import logging
import certifi

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
        # Ensure path doesn't begin with /
        log(f"listing secrets in {path}")
        data = self._request(f"{mount}/metadata/{path.lstrip('/')}", method="LIST")
        return data['keys']


class SecretTree(Tree):
    pass

class KVEngineTab(TabPane):
    def compose(self) -> ComposeResult:
        tree = SecretTree("Secrets", id="secrets")
        tree.show_root = False
        tree.root.expand()
        yield tree

    def _get_node_fullpath(self, node: TreeNode) -> str:
        path = str(node.label)
        while (node := node.parent).is_root is False:
            path = f"{str(node.label)}{path}"
        return path

    def _list_secrets(self, parent_node: TreeNode, path: str = "/"):
        for secret in self.app.server.list_secrets("secret", path):
            parent_node.add_leaf(secret)

    def on_mount(self) -> ComposeResult:
        tree = self.query_one("#secrets") # type: Tree
        self._list_secrets(tree.root)

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        # log(self._get_node_fullpath(event.node))
        self._list_secrets(event.node, self._get_node_fullpath(event.node))
        # log(event.node.label)
        # # event.node.add_leaf("test")
        event.node.expand_all()

class VaultApp(App):
    CSS_PATH = "vault.css"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabbedContent(id="tabs")
        yield Static(id="debug")
        yield Footer()

    def on_mount(self) -> ComposeResult:
        # Create a tab for each engine
        self.server = VaultServer()
        tabs = self.query_one("#tabs")  # type: TabbedContent
        for name, properties in self.server.mounts().items():
            if properties['type'] in ['kv']:
                tabs.add_pane(KVEngineTab(name))
            else:
                tabs.add_pane(TabPane(name))


if __name__ == '__main__':
    # Ensure vault variables are defined
    try:
        os.environ['VAULT_ADDR']
        os.environ['VAULT_TOKEN']
    except KeyError:
        print("Neither VAULT_ADDR or VAULT_TOKEN are defined", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[TextualHandler()],
    )
    app = VaultApp()
    app.run()

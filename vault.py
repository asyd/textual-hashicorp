#!/usr/bin/env python3

from rich.text import TextType
from textual.widget import Widget
from backends import VaultServer
from textual import log
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Tree,
    TabbedContent,
    Static,
    TabPane,
    DataTable
)
from textual.widgets.tree import TreeNode
from textual.logging import TextualHandler
from rich.text import Text

import os
import sys
import logging
import pyperclip

logger = logging.getLogger(__name__)


class KVSecretDetails(DataTable):
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        # paste secret to clipboard
        secret = str(self.get_row_at(event.cursor_row)[1])
        pyperclip.copy(secret)

class KVEngineTab(TabPane):
    def __init__(self, title: TextType, mountpoint: str, *children: Widget, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False):
        self.mountpoint = mountpoint
        super().__init__(title, *children, name=name, id=id, classes=classes, disabled=disabled)


    def compose(self) -> ComposeResult:
        tree = Tree(f"Secrets in {self.mountpoint}", id="secrets")
        tree.show_root = False
        tree.root.expand()
        yield tree
        yield KVSecretDetails(id="details")

    def on_mount(self) -> ComposeResult:
        tree = self.query_one(Tree) # type: Tree
        tree.focus()
        self._list_secrets(tree.root)
        table = self.query_one(KVSecretDetails)
        table.cursor_type = "row"

    def _get_node_fullpath(self, node: TreeNode) -> str:
        # Build full path from current node to engine mountpoint
        path = str(node.label)
        while (node := node.parent).is_root is False:
            path = f"{str(node.label)}{path}"
        return path

    def _list_secrets(self, parent_node: TreeNode, path: str = "/"):
        for secret in self.app.server.list_secrets(self.mountpoint, path):
            parent_node.add_leaf(secret)

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        # is current label a leaf?
        if str(event.node.label[-1]) == '/':
            # yes, so add children
            event.node.remove_children()
            self._list_secrets(event.node, self._get_node_fullpath(event.node))
            event.node.expand_all()
        else:
            # no, display secret content
            secrets = self.app.server.get_secret(
                self.mountpoint,
                self._get_node_fullpath(event.node)
            )
            details_panel = self.query_one(DataTable) # type: DataTable
            details_panel.clear(columns=True)
            details_panel.add_columns('key', 'value')
            for k, v in secrets.items():
                details_panel.add_row(k, Text(v))

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
        tabs = self.query_one(TabbedContent)  # type: TabbedContent
        for name, properties in self.server.mounts().items():
            if properties['type'] in ['kv']:
                tabs.add_pane(KVEngineTab(name, name))
            else:
                tabs.add_pane(TabPane(name))
        self.app.set_focus(tabs)


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

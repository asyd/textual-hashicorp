# About

[Textualize](https://textual.textualize.io/) based tools to interact with some HashiCorp tools.

## Demos

### Vault

[![asciicast](https://asciinema.org/a/wj4XoY4O2hKM2rTKWJkLC51Bh.svg)](https://asciinema.org/a/wj4XoY4O2hKM2rTKWJkLC51Bh)

### Nomad

# Installation

## Requirements

* python >= 3.10
* poetry >= 1.2


Ensure you have `poetry` installed (version >= 1.2), then:

```bash
git clone https://github.com/asyd/nomad-textual.git
cd nomad-textual
poetry install
poetry run python3 nomad.py
poetry run python3 vault.py
```


# Vault

`vault.py` use environment variables expected by `vault` CLI.

Following environment variables are supported:

| Variable          | Mandatory |
|-------------------|:-----------:|
| VAULT_ADDR        |     ✅     |
| VAULT_TOKEN       |     ✅     |

## Launch demo

```bash
cd demo/vault
docker compose up --build --detach --wait
cd ../../
export VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=root
poetry run python3 vault.py
```

## Features

| Backend | Current status |
|---------|---------|
| K/V Version 1 | Not tested but should work |
| K/V Version 2 | Read only |
| PKI | Planned |

# Nomad

`nomad.py` use environment variables expected by `nomad` CLI.

Following environment variables are supported:

| Variable          | Mandatory |
|-------------------|:-----------:|
| NOMAD_ADDR        |     ✅    |
| NOMAD_TOKEN       |           |
| NOMAD_CLIENT_CERT |           |
| NOMAD_CLIENT_KEY  |           |
| NOMAD_NAMESPACE   |           |

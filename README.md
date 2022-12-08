# About

This tool allow live monitoring of all tasks running in a Nomad cluster.

# Requirements

* python >= 3.10
* poetry >= 1.2

## Usage

Ensure you have `poetry` installed (version >= 1.2), then:

```bash
git clone https://github.com/asyd/nomad-textual.git
cd nomad-textual
poetry install
poetry run python3 console.py
```

Before run the tool, 

# Configuration

nomad-textual use environment variables expected by `nomad` CLI.

Following environment variables are supported:

| Variable          | Mandatory |
|-------------------|-----------|
| NOMAD_ADDR        |     x     |
| NOMAD_TOKEN       |           |
| NOMAD_CLIENT_CERT |           |
| NOMAD_CLIENT_KEY  |           |
| NOMAD_NAMESPACE   |           |

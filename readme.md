# qbittorrent-exporter
This application queries a [qBittorrent](https://github.com/qbittorrent/qBittorrent/) instance for its current state and exports it as prometheus-compatible metrics.

## Running
`qbittorrent-exporter` may be run directly on a host with a venv, or as a docker container.

### venv
To prepare the venv, download this project's code to your chosen directory, then open that directory in a terminal and run:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Next, configure the server by creating a config file from [Configuration](#configuration), such as:
```yaml
qbittorrent_url: http://your-qbittorrent-url.local/
qbittorrent_username: admin
qbittorrent_password: password

exporter_port: 8000
```

Finally, to start the server, run:
```bash
.venv/bin/python3 src/prometheus.py <config file>
```

### Docker
Create a compose file with your desired [configuration](#configuration), such as:
```yaml
services:
  qbittorrent-exporter:
    image: ghcr.io/pandomyy/qbittorrent-exporter:latest
    secrets:
      - username
      - password
    environment:
      - QBITEXPORTER_QBITTORRENT_URL=http://your-qbittorrent-url.local/
      - QBITEXPORTER_QBITTORRENT_USERNAME_FILE=/run/secrets/username
      - QBITEXPORTER_QBITTORRENT_PASSWORD_FILE=/run/secrets/password
    ports:
      - 8000:8000
    restart: unless-stopped

secrets:
  username:
    file: ./secrets/username
  password:
    file: ./secrets/password
```

And run with `docker compose up -d`.

## Configuration
The exporter supports configuration by config file and by environment variables.

Config File Key | Environment Variable | Description
--- | --- | ---
qbittorrent_url | QBITEXPORTER_QBITTORRENT_URL | The base URL of your qBittorrent instance
qbittorrent_username | QBITEXPORTER_QBITTORRENT_USERNAME | Your qBittorrent username*
qbittorrent_password | QBITEXPORTER_QBITTORRENT_PASSWORD | Your qBittorrent password*
exporter_port | QBITEXPORTER_EXPORTER_PORT | (default: 8000) The port to listen on

\* If running the exporter on the same machine or within the same docker network as your qBittorrent instance, you may configure qBittorrent's web UI to bypass authentication for clients on localhost. This way, you can omit the username and password from your configuration.

Additionally, when configuring via environment variables, any config options may be suffixed with `_FILE`, in which case the exporter will read the content of the config option from the given file. This is particularly useful when used with [Docker secrets](https://docs.docker.com/compose/how-tos/use-secrets/).


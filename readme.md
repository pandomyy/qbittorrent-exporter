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


## Metrics

### Global metrics
The following are metrics exposed by the exporter that reflect the global state of qbittorrent. They have no labels.

Metric name | Description
--- | ---
qbittorrent_global_alltime_uploaded_bytes_total | The total amount this client has uploaded
qbittorrent_global_alltime_downloaded_bytes_total | The total amount this client has downloaded
qbittorrent_global_session_uploaded_bytes_total | The amount this client has uploaded in the current session
qbittorrent_global_session_downloaded_bytes_total | The amount this client has uploaded in the current session

Note that all of these metrics include metadata and connection data transfers. So, for example, the `downloaded` metrics will continue to go up while seeding torrents as the client downloads information about peers, even if none of yours are incomplete. To get the download/upload numbers for just the torrent content, `sum` the equivalent torrent metrics.

### Torrent metrics
The following metrics describe a single torrent, and so are each repeated for every torrent currently in qbittorrent. As such, every metric has a `name` label for the name of the torrent it's describing.

Metric name | Description
--- | ---
qbittorrent_torrent_downloaded_bytes_total | The amount downloaded for this torrent, excluding any parts that have been marked as 'Do not download' 
qbittorrent_torrent_total_downloaded_bytes_total | The amount downloaded for this torrent, including any parts that have been marked as 'Do not download'
qbittorrent_torrent_uploaded_bytes_total | The amount uploaded for this torrent
qbittorrent_torrent_size_bytes | The size of this torrent, not including any parts marked as 'Do not download'
qbittorrent_torrent_eta_seconds | The estimated time remaining until a download receives everything available or an upload reaches its configured seeding limit
qbittorrent_torrent_total_seeds | The number of seeds for this torrent in the swarm
qbittorrent_torrent_connected_seeds | The number of seeds the client is connected to for this torrent
qbittorrent_torrent_total_leeches | The number of peers/leeches for this torrent in the swarm
qbittorrent_torrent_connected_leeches | The number of peers/leeches the client is connected to for this torrent
qbittorrent_torrent_last_activity_timestamp_seconds | The unix timestamp of when the client was last able to download or upload anything for this torrent

Additionally, there is an info metric named `qbittorrent_torrent_info` which contains the state and several other pieces of stable data as labels:

Label name | Description
--- | ---
name | The name of this torrent, as with the other torrent metrics
state | The current state of this torrent; see [the qbittorrent docs](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#get-torrent-list) for possible values.
category | This torrent's assigned category
hash | This torrent's hash
total_size_bytes | This torrent's total size, including parts marked as 'Do not download'
added_timestamp_seconds | A Unix timestamp of when this torrent was added to the client
completed_timestamp_seconds | A Unix timestamp of when this torrent completed downloading, or `0` if it is still incomplete

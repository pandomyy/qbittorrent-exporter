import signal
import types
import typing

import prometheus_client as prometheus
import prometheus_client.core as prometheus_core
import prometheus_client.registry as prometheus_registry

from config import get_config
from qbittorrent import query_qbit_api


# These types include only relevant fields from the API response.

# There is not currently documentation on these fields.
class QBitMainDataServerState(typing.TypedDict):
	alltime_dl: int
	alltime_ul: int
	dl_info_data: int # total downloaded this session
	up_info_data: int # total uploaded this session

# Remaining fields can be found at:
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#get-torrent-list
class QBitMainDataTorrent(typing.TypedDict):
	name: str
	amount_left: int
	downloaded: int
	uploaded: int
	eta: int
	num_complete: int # all seeds
	num_incomplete: int # all leechs
	num_leechs: int
	num_seeds: int
	size: int # total_size - (parts of torrent marked as 'Do not download')
	total_size: int
	last_activity: int # time of last activity
	time_active: int
	seeding_time: int
	state: str
	added_on: int # unix time of creation
	completion_on: int # unix time of completion
	category: str
	infohash_v1: str
	infohash_v2: str

# Remaining fields can be found at:
# https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#get-main-data
class QBitMainData(typing.TypedDict):
	server_state: QBitMainDataServerState
	torrents: dict[str, QBitMainDataTorrent]


collector_prefix = "qbittorrent"
global_prefix = f"{collector_prefix}_global"
torrent_prefix = f"{collector_prefix}_torrent"

torrent_label_names = ["name"]

class QBittorrentCollector(prometheus_registry.Collector):
	def collect_global_metrics(
		self,
		maindata: QBitMainData,
	) -> typing.Iterable[prometheus.Metric]:
		yield prometheus_core.CounterMetricFamily(
			f"{global_prefix}_alltime_uploaded",
			"The total amount of bytes uploaded with this client",
			value=maindata["server_state"]["alltime_ul"],
			unit="bytes",
		)

		yield prometheus_core.CounterMetricFamily(
			f"{global_prefix}_alltime_downloaded",
			"The total amount of bytes downloaded with this client",
			value=maindata["server_state"]["alltime_dl"],
			unit="bytes",
		)

		yield prometheus_core.CounterMetricFamily(
			f"{global_prefix}_session_uploaded",
			"The total amount of bytes uploaded with this client",
			value=maindata["server_state"]["alltime_ul"],
			unit="bytes",
		)

		yield prometheus_core.CounterMetricFamily(
			f"{global_prefix}_session_downloaded",
			"The total amount of bytes downloaded with this client",
			value=maindata["server_state"]["alltime_dl"],
			unit="bytes",
		)

	def collect_torrent_completion_metrics(
		self,
		maindata: QBitMainData,
	) -> typing.Iterable[prometheus.Metric]:
		total_downloaded = prometheus_core.CounterMetricFamily(
			f"{torrent_prefix}_total_downloaded",
			"The total amount downloaded for a torrent, including even sections subsequently marked as 'Do not download'",
			labels=torrent_label_names,
			unit="bytes",
		)
		relevant_downloaded = prometheus_core.CounterMetricFamily(
			f"{torrent_prefix}_downloaded",
			"The amount downloaded for a torrent, including only sections marked for download",
			labels=torrent_label_names,
			unit="bytes",
		)

		total_uploaded = prometheus_core.CounterMetricFamily(
			f"{torrent_prefix}_uploaded",
			"The total amount uploaded for a torrent, including sections subsequently marked as 'Do not download'",
			labels=torrent_label_names,
			unit="bytes",
		)

		total_size = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_total_size",
			"The total size of a torrent, including sections marked as 'Do not download'",
			labels=torrent_label_names,
			unit="bytes",
		)
		size = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_size",
			"The size of a torrent, including only sections marked for download",
			labels=torrent_label_names,
			unit="bytes",
		)

		eta = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_eta",
			"The estimated time remaining for a torrent",
			labels=torrent_label_names,
			unit="seconds",
		)

		for torrent in maindata["torrents"].values():
			labels = [torrent["name"]]

			total_downloaded.add_metric(labels, torrent["downloaded"])
			relevant_downloaded.add_metric(
				labels,
				# As far as I can tell, this is the only way to get this value.
				torrent["size"] - torrent["amount_left"],
			)

			total_uploaded.add_metric(labels, torrent["uploaded"])

			total_size.add_metric(labels, torrent["total_size"])
			size.add_metric(labels, torrent["size"])

			eta.add_metric(labels, torrent["eta"])
		
		return [
			total_downloaded,
			relevant_downloaded,
			total_uploaded,
			total_size,
			size,
			eta,
		]
	
	def collect_torrent_connection_metrics(
		self,
		maindata: QBitMainData,
	) -> typing.Iterable[prometheus.Metric]:
		total_seeds = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_total_seeds",
			"The total amount of known seeds for a torrent",
			labels=torrent_label_names,
		)
		connected_seeds = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_connected_seeds",
			"The amount of seeds for a torrent which are curently connected to the client",
			labels=torrent_label_names,
		)

		total_leeches = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_total_leeches",
			"The total amount of known leeches for a torrent",
			labels=torrent_label_names,
		)
		connected_leeches = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_connected_leeches",
			"The amount of leeches for a torrent which are curently connected to the client",
			labels=torrent_label_names,
		)

		time_of_last_activity = prometheus_core.GaugeMetricFamily(
			f"{torrent_prefix}_last_activity",
			"The timestamp of when a torrent was last active",
			labels=torrent_label_names,
			unit="timestamp_seconds",
		)

		for torrent in maindata["torrents"].values():
			labels = [torrent["name"]]

			total_seeds.add_metric(labels, torrent["num_complete"])
			connected_seeds.add_metric(labels, torrent["num_seeds"])

			total_leeches.add_metric(labels, torrent["num_incomplete"])
			connected_leeches.add_metric(labels, torrent["num_leechs"])

			time_of_last_activity.add_metric(labels, torrent["last_activity"])

		return [
			total_seeds,
			connected_seeds,
			total_leeches,
			connected_leeches,
			time_of_last_activity,
		]
	
	def collect_torrent_info_metrics(
		self,
		maindata: QBitMainData,
	) -> typing.Iterable[prometheus.Metric]:
		torrent_info = prometheus.core.InfoMetricFamily(
			f"{torrent_prefix}",
			"The constant information of a torrent",
			labels=torrent_label_names,
		)

		for torrent in maindata["torrents"].values():
			labels = [torrent["name"]]

			torrent_info.add_metric(
				labels,
				{
					"state": torrent["state"],
					"category": torrent["category"],
					"hash": torrent["infohash_v1"] or torrent["infohash_v2"],
					"total_size_bytes": str(torrent["total_size"]),
					"added_timestamp_seconds": str(torrent["added_on"]),
					"completed_timestamp_seconds": str(
						torrent["completion_on"],
					),
				},
			)

		return [
			torrent_info,
		]
		

	def collect(self) -> typing.Iterable[prometheus.Metric]:
		maindata: QBitMainData = query_qbit_api("sync/maindata")

		yield from self.collect_global_metrics(maindata)
		yield from self.collect_torrent_info_metrics(maindata)
		yield from self.collect_torrent_completion_metrics(maindata)
		yield from self.collect_torrent_connection_metrics(maindata)


if __name__ == "__main__":
	config = get_config()

	prometheus_core.REGISTRY.register(QBittorrentCollector())
	server, thread = prometheus.start_http_server(config["exporter_port"])
	print("Started qbittorrent-exporter server")

	def shutdown(_sigtype: int, _frame: types.FrameType | None) -> None:
		print("Stopping qbittorrent-exporter server")
		server.shutdown()

	signal.signal(signal.SIGINT, shutdown)
	signal.signal(signal.SIGTERM, shutdown)
	thread.join()

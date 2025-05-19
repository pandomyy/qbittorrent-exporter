import json
import typing
import urllib.parse

import requests

from config import get_config


_session_cookie: str | None = None
def login() -> None:
	config = get_config()

	global _session_cookie
	response = requests.post(
		urllib.parse.urljoin(
			config["qbittorrent_url"],
			"/api/v2/auth/login",
		),
		{
			"username": config["qbittorrent_username"],
			"password": config["qbittorrent_password"],
		}
	)
	_session_cookie = response.cookies["SID"]


def _make_request(path: str, retried: bool = False) -> typing.Any:
	config = get_config()

	global _session_cookie

	response = requests.get(
		urllib.parse.urljoin(
			config["qbittorrent_url"],
			"api/v2/" + path if not path.startswith("/") else path[1:],
		),
		cookies={
			"SID": _session_cookie or "",
		},
	)

	if response.status_code == 403:
		if not retried:
			login()
		
		else:
			raise Exception("Failed to log in to qbittorrent")

		return _make_request(path, True)

	return json.loads(response.text)


def query_qbit_api(path: str) -> typing.Any:
	return _make_request(path, False)

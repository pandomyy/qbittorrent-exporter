import os
import sys
import typing

import yaml


class Config(typing.TypedDict):
	qbittorrent_url: str
	qbittorrent_username: str
	qbittorrent_password: str

	exporter_port: int

_default_config: Config = {
	"qbittorrent_url": None, # type: ignore[typeddict-item]
	"qbittorrent_username": None, # type: ignore[typeddict-item]
	"qbittorrent_password": None, # type: ignore[typeddict-item]
	"exporter_port": 8000,
}

env_var_prefix = "QBITEXPORTER_"

_config: Config | None = None
def _load_config() -> None:
	global _config

	_config = _default_config.copy()
	
	# Use the a provided config file, if any
	if len(sys.argv) > 1:
		config_name = sys.argv[1]
		config_path = os.path.join(os.getcwd(), config_name)

		with open(config_path) as file:
			_config = {**_config, **yaml.load(file, Loader=yaml.BaseLoader)}
	
	# Use config options from environment variable configuration
	for config_key in _default_config.keys():
		env_var_name = env_var_prefix + config_key.upper()
		file_env_var_name = f"{env_var_name}_FILE"

		# Comments disable type checking on a few lines here due to the type
		# 	checker not being sophisticated enough to tell that `config_key`
		# 	will always be a valid key of `Config`.
		if file_env_var_name in os.environ:
			with open(os.environ[file_env_var_name]) as file:
				_config[config_key] = ( # type: ignore[literal-required]
					file.read()
				)
		
		elif env_var_name in os.environ:
			_config[config_key] = ( # type: ignore[literal-required]
				os.environ[env_var_name]
			)
	
	# This option may have been read as a string, so we coerce it.
	_config["exporter_port"] = int(_config["exporter_port"])

	if _config["qbittorrent_url"] is None:
		raise Exception(
			"Configuration error: no qbittorrent URL has been provided",
		)


def get_config() -> Config:
	global _config

	if _config is None:
		_load_config()

	return typing.cast(Config, _config)

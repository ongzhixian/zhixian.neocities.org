"""
Script to sync files from local directory to neocities
Classes:
    AppLogger
    AppConfiguration
    SecretsManager
    NeocitiesClient
    FileSyncManager

"""
import os
import json
import subprocess
import logging

import requests

import pdb

NEOCITIES_BASE_API_URL = "https://neocities.org/api"

class AppLogger:
    """A simple logger wrapper around Python's logging module.
    Logs to both console and file.
    """

    def __init__(self, name=None, log_file_name=None, level=logging.INFO):
        if name is None: name = self.__class__.__module__
        if log_file_name is None: log_file_name = f"{os.path.basename(__file__).replace('.py', '')}.log"
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Create file handler
        fh = logging.FileHandler(log_file_name)
        fh.setFormatter(formatter)
        # Create console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)


# Instantiate a global logger for use throughout the module.
logger = AppLogger()


class AppConfiguration:
    """Handles loading and saving sync configuration."""

    def __init__(self, configuration_file_name=None):
        if configuration_file_name is None:
            configuration_file_name = f"{os.path.basename(__file__).replace('.py', '')}-config.json"

        self.configuration_file_name = configuration_file_name
        logger.debug(f"Configuration file name '{self.configuration_file_name}'.")

        self.config = self.load_config()
        logger.debug(f"Configuration loaded.")

    def load_config(self):
        try:
            with open(self.configuration_file_name, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file '{self.configuration_file_name}' not found.")
            return {}

    def save_config(self):
        with open(self.configuration_file_name, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)
        logger.info(f"Sync config saved to '{self.configuration_file_name}'.")

    def get(self, key_path, default=None):
        keys = key_path.split(':')
        current_data = self.config

        for key in keys:
            if isinstance(current_data, dict) and key in current_data:
                current_data = current_data[key]
            else:
                return default
        return current_data


    def update(self, key_path, value):
        keys = key_path.split(':')
        current_data = self.config

        for i, key in enumerate(keys):
            # if is last key in the path (leaf) and current_data is dict
            if i == len(keys) - 1 and isinstance(current_data, dict):
                logger.info(f'Configuration {key_path} saved.')
                current_data[key] = value
                self.save_config()
                return
            else:
                if isinstance(current_data, dict):
                    # Create nested dictionary if it doesn't exist or is not a dict
                    if key not in current_data:
                        current_data[key] = {}
                    # Traverse
                    if isinstance(current_data[key], dict):
                        current_data = current_data[key]

        # Configuration not saved; most likely key_path is not dict
        logger.warning(f'Configuration {key_path} not saved.')


class SecretsManager:
    """Manages retrieval of secrets from the user secrets file."""

    def __init__(self, secrets_file_path):
        self.secrets_file_path = os.path.normpath(os.path.expandvars(secrets_file_path))
        logger.debug(f"Secrets file path '{self.secrets_file_path}'.")

    def get_secrets(self) -> dict:

        try:
            with open(self.secrets_file_path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
                logger.debug(f"Secrets loaded.")
                return secrets
        except Exception as ex:
            logger.error(f"Error reading secrets file at '{self.secrets_file_path}': {ex}")
            raise


class NeocitiesClient:
    """Client for interacting with the Neocities API."""

    def __init__(self, api_key, base_url=NEOCITIES_BASE_API_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        logger.debug("NeocitiesClient initialized.")

    def get_site_info(self):
        url = f"{self.base_url}/info"
        logger.debug(f"Fetching site info from {url}.")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            logger.info("Site info successfully retrieved.")
            return response.json()
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error when fetching site info: {http_err}")
        except Exception as err:
            logger.error(f"Unexpected error in get_site_info: {err}")

    def get_site_file_list(self):
        url = f"{self.base_url}/list"
        logger.debug(f"Fetching file list from {url}.")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            logger.info("Site file list retrieved successfully.")
            return response.json()
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error when fetching file list: {http_err}")
        except Exception as err:
            logger.error(f"Unexpected error in get_site_file_list: {err}")

    def upload_file(self, file_path):
        url = f"{self.base_url}/upload"
        logger.info(f"Uploading file {file_path} to {url}.")
        cwd = os.getcwd()
        try:
            with open(file_path, "rb") as f:
                remote_path = os.path.normpath(file_path.replace(cwd, '')).replace('\\','/')
                print('remote_path', remote_path)
                files = {remote_path: f}
                response = requests.post(url, files=files, headers=self.headers)
                response.raise_for_status()
                logger.info(f"Successfully uploaded {file_path}: {response.text}")
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error uploading {file_path}: {http_err}")
        except Exception as err:
            logger.error(f"Error uploading {file_path}: {err}")

    def get_site_info_using_curl(self):
        """Alternative method using curl subprocess."""
        url = f"{self.base_url}/info"
        logger.debug(f"Fetching site info using curl from {url}.")
        try:
            result = subprocess.run(
                ["curl.exe", "-H", f"Authorization: Bearer {self.api_key}", url],
                stdout=subprocess.PIPE,
                check=True,
            )
            output_str = result.stdout.decode("utf-8")
            logger.info("Site info successfully retrieved using curl.")
            return json.loads(output_str)
        except Exception as err:
            logger.error(f"Error fetching site info using curl: {err}")


class FileSyncManager:
    """Manages file synchronization based on modification timestamps."""

    def __init__(self, directory, sync_config:AppConfiguration):
        self.directory = os.path.normpath(directory)
        self.sync_config = sync_config

        self.ignore_file_list = set(sync_config.get('sync:ignore_file_list', ''))
        ignore_file_path_list = sync_config.get('sync:ignore_paths', [])
        ignore_file_path_list = set(map(lambda ignore_file_path: os.path.normpath(ignore_file_path), ignore_file_path_list))
        self.ignore_file_path_list = ignore_file_path_list

        self.config_key = 'sync:last-max-timestamp'
        self.prev_timestamp = self.sync_config.get(self.config_key)
        if self.prev_timestamp:
            logger.debug(f"Previous last-max-timestamp: {self.prev_timestamp}")

    def __is_in_ignore_file_path_list(self, root_path):
        for ignore_file_path in self.ignore_file_path_list:
            if ignore_file_path in root_path:
                return True
        return False

    def scan_files(self):
        """Scan a directory and return a list of file paths to upload

        Note: There are 3 log ignore statuses:
            [IGNORE-(P)] : File path in ignore_paths
            [IGNORE-(F)] : File name in ignore_file_list
            [IGNORE-(T)] : File timestamp <= last-max-timestamp
        """
        file_list = []
        latest_timestamp = None

        logger.debug(f"Target scan directory '{self.directory}'")
        logger.info(f"Scanning directory for updated or new files.")
        for root, _, files in os.walk(self.directory):
            # Ignore file paths in the ignore_file_path_list
            if self.__is_in_ignore_file_path_list(root):
                logger.debug(f"{'IGNORE-(P)':<10} {root}.")
                continue

            for file_name in files:
                src_path = os.path.join(root, file_name)

                # Ignore file names in the ignore_file_list
                if file_name in self.ignore_file_list:
                    logger.debug(f"{'IGNORE-(F)':<10} {src_path}.")
                    continue

                # Check timestamp of files
                file_timestamp = os.path.getmtime(src_path)

                # If file timestamp is larger than last-max-timestamp, copy file
                if self.prev_timestamp is None or file_timestamp > self.prev_timestamp:
                    file_list.append(src_path)
                    logger.info(f"ADD: {src_path}")
                    if latest_timestamp is None or file_timestamp > latest_timestamp:
                        latest_timestamp = file_timestamp
                else:
                    logger.debug(f"{'IGNORE-(T)':<10} {src_path}.")

        if latest_timestamp is not None:
            logger.info(f"Latest file timestamp: {latest_timestamp}")
            self.sync_config.update(self.config_key, latest_timestamp)
        else:
            logger.info("No new or modified files found.")

        return file_list


def main():

    # Load synchronization configuration.
    app_configuration = AppConfiguration()
    secrets_file_path = app_configuration.get('secrets:tech-notes-press')
    api_secret_key = app_configuration.get('secrets:api-secret-key')

    # Retrieve API key from secrets.
    secrets = SecretsManager(secrets_file_path).get_secrets()
    if api_secret_key not in secrets:
        logger.error("neocities_api_key is not defined in secrets. Exiting...")
        exit(1)
    api_key = secrets[api_secret_key]
    logger.debug("API key retrieved successfully.")

    # Scan local directory for updated or new files.
    current_directory = os.getcwd()
    file_sync = FileSyncManager(current_directory, app_configuration)
    files_to_upload = file_sync.scan_files()

    # Initialize the Neocities client.
    client = NeocitiesClient(api_key)

    # Upload new or modified files.
    for file_path in files_to_upload:
        client.upload_file(file_path)

    # Get site information and the current file list.
    # site_info = client.get_site_info()
    # if site_info:
    #     logger.info(f"Site Info: {site_info}")

    # Get remote site files count
    # files_info = client.get_site_file_list()
    # if files_info:
    #     files_on_site = files_info.get("files", [])
    #     logger.info(f"File record count on site: {len(files_on_site)}")
    #
    #     # Filter for actual file entries only
    #     file_path_list = []
    #     for file_entry in files_on_site:
    #         if not file_entry["is_directory"]:
    #             file_path_list.append(file_entry["path"])
    #     logger.info(f"Actual file count: {len(file_path_list)}.")


if __name__ == "__main__":
    main()

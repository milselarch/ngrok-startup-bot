import subprocess
import requests
import time

from result import Ok, Err, Result
from typing import List, Dict
from requests.exceptions import RequestException


class NgrokNotRunningError(RuntimeError):
    pass


class NgrokManager(object):
    def __init__(
        self, session_name: str = "ngrok_session",
        config_path: str = ""
    ):
        self.session_name = session_name
        self.config_path = config_path
        self.process = None

    @staticmethod
    def load_is_running() -> bool:
        try:
            response = requests.get(
                "http://localhost:4040/api/endpoints", timeout=2
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def load_endpoints(self) -> Result[
        List[Dict], RequestException | NgrokNotRunningError
    ]:
        if not self.load_is_running():
            return Err(NgrokNotRunningError())

        try:
            response = requests.get(
                "http://localhost:4040/api/endpoints"
            )
            endpoints = response.json().get("endpoints", [])
            return Ok(endpoints)
        except RequestException as e:
            return Err(e)

    def start_endpoints_in_tmux(self) -> bool:
        if self.load_is_running():
            return True

        ngrok_cmd = "ngrok start --all"
        if self.config_path:
            ngrok_cmd += f" --config {self.config_path}"

        # Check if session already exists
        check_session = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if check_session.returncode == 0:
            # Kill existing session
            subprocess.run(
                ["tmux", "kill-session", "-t", self.session_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # Create a new tmux session with ngrok
        try:
            subprocess.run([
                "tmux", "new-session", "-d", "-s",
                self.session_name, ngrok_cmd
            ], check=True)

            # Wait for ngrok to initialize
            time.sleep(3)
            return self.load_is_running()
        except Exception as e:
            print(f"Failed to start ngrok in tmux: {e}")
            return False

    def start_endpoints(self, config_path: str = "") -> bool:
        """
        Start all ngrok endpoints defined in config
        """
        if self.load_is_running():
            return True

        cmd = ["ngrok", "start", "--all"]
        if config_path:
            cmd.extend(["--config", config_path])

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait for ngrok to initialize
            time.sleep(3)
            return self.load_is_running()
        except Exception as e:
            print(f"Failed to start ngrok: {e}")
            return False

    def stop_endpoints(self) -> bool:
        """Stop all running ngrok endpoints"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
                self.process = None
            else:
                # Try to kill any existing ngrok processes
                subprocess.run(
                    ["pkill", "ngrok"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            return not self.load_is_running()
        except Exception as e:
            print(f"Failed to stop ngrok: {e}")
            return False

    def restart_endpoints(self, config_path: str = "") -> bool:
        """
        Restart all ngrok endpoints
        """
        self.stop_endpoints()
        time.sleep(1)
        return self.start_endpoints(config_path)

    def get_connection_details(
        self,
    ) -> Result[str, RequestException | NgrokNotRunningError]:
        """
        Return formatted details for active v3 endpoints.
        """
        endpoints_result = self.load_endpoints()

        if endpoints_result.is_err():
            return Err(endpoints_result.unwrap_err())

        endpoints = endpoints_result.unwrap()
        details = []

        for endpoint in endpoints:
            name = endpoint.get("name", "unknown")
            url = (
                endpoint.get("url")
                or endpoint.get("public_url")
                or endpoint.get("hostports")
                or "unknown"
            )

            upstream = endpoint.get("upstream", {})
            upstream_url = (
                upstream.get("url")
                if isinstance(upstream, dict)
                else upstream
            )

            if upstream_url:
                details.append(f"{name}: {url} -> {upstream_url}")
            else:
                details.append(f"{name}: {url}")

        return Ok("\n".join(details))

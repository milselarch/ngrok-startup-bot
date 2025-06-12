import subprocess
import requests
import json
import time
import signal
import os

from result import Ok, Err, Result
from typing import List, Dict, Optional
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
                "http://localhost:4040/api/tunnels", timeout=2
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def load_tunnels(self) -> Result[
        List[Dict], RequestException | NgrokNotRunningError
    ]:
        if not self.load_is_running():
            return Err(NgrokNotRunningError())

        try:
            response = requests.get(
                "http://localhost:4040/api/tunnels"
            )
            tunnels = response.json().get("tunnels", [])
            return Ok(tunnels)
        except RequestException as e:
            return Err(e)

    def start_tunnels_in_tmux(self) -> bool:
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

    def start_tunnels(self, config_path: str = "") -> bool:
        """
        Start all ngrok tunnels defined in config
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

    def stop_tunnels(self) -> bool:
        """Stop all running ngrok tunnels"""
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

    def restart_tunnels(self, config_path: str = "") -> bool:
        """
        Restart all ngrok tunnels
        """
        self.stop_tunnels()
        time.sleep(1)
        return self.start_tunnels(config_path)

    def get_connection_details(self) -> Result[
        str, NgrokNotRunningError | RequestException
    ]:
        """
        Get formatted connection details for all tunnels
        """
        load_tunnels_res = self.load_tunnels()
        if load_tunnels_res.is_err():
            return load_tunnels_res

        tunnels = load_tunnels_res.unwrap()
        details = []

        for tunnel in tunnels:
            name = tunnel.get('name', 'unknown')
            url = tunnel.get('public_url', 'unknown')
            proto = tunnel.get('proto', 'unknown')
            details.append(f"{name} ({proto}): {url}")

        return Ok("\n".join(details))

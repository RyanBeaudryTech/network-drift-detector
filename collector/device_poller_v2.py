import os
import json
import yaml
from scrapli import Scrapli
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "devices.yml"
SNAPSHOT_DIR = "diff_engine/snapshots"

class DevicePoller:
    def __init__(self, config_file=CONFIG_FILE):
        self.devices = self.load_devices(config_file)
        # Define noisy fields to filter from snapshots
        self.fields_to_remove = [
            "uptime",
            "last_change",
            "input_errors",
            "output_errors",
            "packets_in",
            "packets_out",
            "messages_sent",
            "messages_received"
        ]

    def load_devices(self, config_file):
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        return data.get("devices", [])

    def poll_device(self, device):
        connection_params = {
            "host": device["host"],
            "auth_username": device["username"],
            "auth_password": device["password"],
            "auth_strict_key": False,
            "platform": device["device_type"],
            "port": device.get("port", 22),
            "transport": "ssh2",
        }

        commands = {
            "routing_table": "show ip route",
            "interfaces": "show ip interface brief",
            "bgp_neighbors": "show ip bgp summary",
            "arp_table": "show arp",
        }

        try:
            conn = Scrapli(**connection_params)
            conn.open()
        except Exception as e:
            print(f"Error connecting to {device['hostname']}: {e}")
            return {}

        results = {}
        for key, cmd in commands.items():
            output = conn.send_command(cmd).result
            results[key] = output

        conn.close()
        return results

    # ------------------------------
    # Filter function
    # ------------------------------
    def filter_snapshot_data(self, data):
        if isinstance(data, dict):
            return {k: self.filter_snapshot_data(v) for k, v in data.items() if k not in self.fields_to_remove}
        elif isinstance(data, list):
            return [self.filter_snapshot_data(item) for item in data]
        else:
            return data

    # ------------------------------
    # Save results
    # ------------------------------
    def save_results(self, hostname, data):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder = Path(SNAPSHOT_DIR) / hostname
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{timestamp}.json"

        # Filter before saving
        filtered_data = self.filter_snapshot_data(data)

        with open(file_path, "w") as f:
            json.dump(filtered_data, f, indent=4)

    # ------------------------------
    # Poll all devices
    # ------------------------------
    def poll_all(self):
        all_results = {}
        for device in self.devices:
            hostname = device["hostname"]
            print(f"Polling {hostname}...")
            data = self.poll_device(device)
            if data:
                self.save_results(hostname, data)
            all_results[hostname] = data
        return all_results

# ------------------------------
# Main execution
# ------------------------------
if __name__ == "__main__":
    dp = DevicePoller()
    results = dp.poll_all()
    print("Polling complete.")

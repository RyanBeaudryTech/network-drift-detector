import os
import yaml
import json
from datetime import datetime
from scrapli import Scrapli


class DevicePoller:
    def __init__(self, config_file="config/devices.yml"):
        self.devices = self.load_devices(config_file)

    def load_devices(self, config_file):
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
        return data["devices"]

    def poll_device(self, device):
        hostname = device["hostname"]
        print(f"\nPolling {hostname}...")

        connection_params = {
            "host": device["host"],
            "auth_username": device["username"],
            "auth_password": device["password"],
            "auth_strict_key": False,
            "platform": device["device_type"],   # from YAML
            "port": device.get("port", 22),      # default to 22
            "transport": "ssh2",
            "timeout_ops":15,
        }

        commands = {
            "routing_table": "show ip route",
            "interfaces": "show ip interface brief",
            "bgp_neighbors": "show ip bgp summary",
            "arp_table": "show arp",
        }

        try:
            with Scrapli(**connection_params) as conn:
                results = {}

                for key, cmd in commands.items():
                    response = conn.send_command(cmd)
                    results[key] = response.result

                # Save to JSON snapshot
                self.save_results(hostname, results)

                print(f"✔️  Completed {hostname}")

                return results

        except Exception as e:
            print(f"❌ Error connecting to {hostname}: {e}")
            return None

    def save_results(self, hostname, results):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        folder = f"snapshots/{hostname}"
        os.makedirs(folder, exist_ok=True)

        filepath = f"{folder}/{timestamp}.json"

        snapshot = {
            "device": hostname,
            "timestamp": timestamp,
            "results": results,
        }

        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=4)

    def poll_all(self):
        all_results = {}

        for device in self.devices:
            hostname = device["hostname"]
            result = self.poll_device(device)
            all_results[hostname] = result

        return all_results


if __name__ == "__main__":
    poller = DevicePoller()
    poller.poll_all()

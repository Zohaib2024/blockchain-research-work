"""
MultiChain JSON-RPC Client Wrapper for ZohaibChain1
"""

import json
import urllib.request
import base64
import time
from . import config

import os
from . import config

class MultiChainClient:
    def __init__(self, rpc_url=config.RPC_URL, user=config.RPC_USER, password=config.RPC_PASS):
        # Auto-detect credentials from local ~/.multichain/<chain>/multichain.conf if available
        conf_path = os.path.expanduser(f"~/.multichain/{config.CHAIN_NAME}/multichain.conf")
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("rpcuser="):
                        user = line.split("=", 1)[1].strip()
                    elif line.startswith("rpcpassword="):
                        password = line.split("=", 1)[1].strip()
                    elif line.startswith("rpcport="):
                        port = line.split("=", 1)[1].strip()
                        rpc_url = f"http://127.0.0.1:{port}"

        self.rpc_url = rpc_url
        self.user = user
        self.password = password
        auth_str = f"{user}:{password}"
        self.auth_header = "Basic " + base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    def call(self, method, params=None):
        if params is None:
            params = []
        payload = {
            "jsonrpc": "1.0",
            "id": f"zohaibchain-{int(time.time() * 1000)}",
            "method": method,
            "params": params
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.rpc_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": self.auth_header
            }
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("error"):
                    raise RuntimeError(f"RPC Error [{method}]: {result['error']}")
                return result.get("result")
        except urllib.error.HTTPError as e:
            err_content = e.read().decode("utf-8")
            raise RuntimeError(f"HTTPError {e.code} on {method}: {err_content}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"\n[!] MultiChain node '{config.CHAIN_NAME}' is not reachable at {self.rpc_url}.\n"
                f"[i] To start your blockchain node, run:  multichaind {config.CHAIN_NAME} -daemon\n"
                f"[i] Or run the automated setup script:  bash setup_chain.sh\n"
                f"Underlying error: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Exception calling {method}: {e}")

    def get_info(self):
        return self.call("getinfo")

    def get_new_address(self):
        return self.call("getnewaddress")

    def grant_permissions(self, address, perms="send,receive,write"):
        return self.call("grant", [address, perms])

    def publish_stream(self, stream_name, key, data_dict):
        """
        Publishes JSON metadata entry to a MultiChain stream with an indexable key.
        """
        hex_data = json.dumps(data_dict).encode("utf-8").hex()
        return self.call("publish", [stream_name, str(key), hex_data])

    def read_stream_items(self, stream_name, count=100):
        items = self.call("liststreamitems", [stream_name, False, count])
        parsed = []
        for item in (items or []):
            raw_data = item.get("data")
            parsed_json = {}
            if raw_data:
                try:
                    bytes_data = bytes.fromhex(raw_data)
                    parsed_json = json.loads(bytes_data.decode("utf-8"))
                except Exception:
                    parsed_json = {"raw": raw_data}
            parsed.append({
                "txid": item.get("txid"),
                "key": item.get("key"),
                "publishers": item.get("publishers"),
                "time": item.get("time"),
                "blocktime": item.get("blocktime"),
                "data": parsed_json
            })
        return parsed

    def read_stream_key_items(self, stream_name, key, count=100):
        items = self.call("liststreamkeyitems", [stream_name, str(key), False, count])
        parsed = []
        for item in (items or []):
            raw_data = item.get("data")
            parsed_json = {}
            if raw_data:
                try:
                    bytes_data = bytes.fromhex(raw_data)
                    parsed_json = json.loads(bytes_data.decode("utf-8"))
                except Exception:
                    parsed_json = {"raw": raw_data}
            parsed.append({
                "txid": item.get("txid"),
                "key": item.get("key"),
                "publishers": item.get("publishers"),
                "time": item.get("time"),
                "blocktime": item.get("blocktime"),
                "data": parsed_json
            })
        return parsed

    def send_asset(self, to_address, asset_name, amount):
        return self.call("sendasset", [to_address, asset_name, amount])

    def get_asset_balance(self, address, asset_name):
        balances = self.call("getaddressbalances", [address])
        for b in (balances or []):
            if b.get("name") == asset_name:
                return b.get("qty", 0)
        return 0

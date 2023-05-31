# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import logging
import requests
import json
from eth_abi import decode_abi, encode_abi
from Crypto.Hash import keccak

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]

ERC20_TRANSFER_HEADER =  b'Y\xda*\x98N\x16Z\xe4H|\x99\xe5\xd1\xdc\xa7\xe0L\x8a\x990\x1b\xe6\xbc\t)2\xcb]\x7f\x03Cx'

k = keccak.new(digest_bits=256)
k.update(b'executeSwap(address,uint,address,address)')
SWAP_FUNCTION = k.digest()[:4] # first 4 bytes 


logger.info(f"HTTP rollup_server url is {rollup_server}")

def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")

def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()

def post(endpoint, json):
    response = requests.post(f"{rollup_server}/{endpoint}", json=json)
    logger.info(f"Received {endpoint} status {response.status_code} body {response.content}")


def handle_advance(data):
    logger.info(f"Received advance request data {data}")

    status = "accept"
    try:
        if data["metadata"]["msg_sender"] != rollup_address:
            raise Exception(f"Input does not come from the Portal", data["payload"])
        
        binary = hex2str(data["payload"])

        # decode payload
        (input_header, depositor, depositedERC20,
         amount, deposit_data) = decode_abi(['bytes32', 'address', 'address', 'uint256', 'bytes'], binary)
        
        
        if input_header != ERC20_TRANSFER_HEADER:
            raise Exception(f"Input header is not from an ERC20 transfer", data["payload"])

        swapper_contract, desiredERC20 = decode_abi(['address', 'address'], deposit_data)

        notice = {
            "timestamp": data["metadata"]["timestamp"],
            "msg_sender": depositor,
            "depositedERC20Token": depositedERC20,
            "amount": amount,
            "desiredERC20Token": desiredERC20
        }

        post("notice", {"payload": str2hex(json.dumps(notice))})
        
        voucher_payload = SWAP_FUNCTION + encode_abi(["address", "uint", "address", "address"], [depositedERC20, amount, depositor, desiredERC20])
        voucher = {"address": swapper_contract, "payload": "0x" + voucher_payload.hex()}
        post("voucher", voucher)

    except Exception as e:
        status = "reject"
        post("report", {"payload": str2hex(str(e))})

    return status

def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    logger.info("Adding report")

    inspect_response = "Voucher to trade assets example."
    inspect_response_hex = str2hex(inspect_response)
    post("report", {"payload": inspect_response_hex})
    return "accept"

handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}
rollup_address = None

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        if "metadata" in data:
            metadata = data["metadata"]
            if metadata["epoch_index"] == 0 and metadata["input_index"] == 0:
                rollup_address = metadata["msg_sender"]
                logger.info(f"Captured rollup address: {rollup_address}")
                continue
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])

#!/usr/bin/env python3
"""
erc8004_agent_demo.py - The AGENT side of the Sepolia PoC.

Makes a real Markovian stamp, then submits validationRequest on the Sepolia
ValidationRegistry naming our validator. Prints the merkle_root, requestHash, and the
Etherscan tx link. After this, run erc8004_relayer.py --once to post the response.

For the PoC the agent wallet == the validator wallet (one funded Sepolia key); the
contract lets any address request. requestURI = the stamp verify_url (embeds the root).

Run: /Users/colinwinter/neo_env/bin/python3 erc8004_agent_demo.py [--agent-id N]
"""
import json, sys, time, argparse
from pathlib import Path
import requests
from web3 import Web3
from eth_account import Account

HERE   = Path(__file__).resolve().parent
CONFIG = Path.home() / ".erc8004_poc_config"
UA = "python-httpx/0.27.0"
STAMP_API = "https://api.quantsynth.net/stamp"
STAMP_WALLET = "135nd7CXWJ8QRjuCDkXoM5oxx9MKc7YNjN"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--agent-id", type=int, default=1)
    args = ap.parse_args()
    cfg = json.loads(CONFIG.read_text())
    abi = json.loads((HERE / "validation_compiled.json").read_text())["abi"]
    w3 = Web3(Web3.HTTPProvider(cfg["rpc_url"], request_kwargs={"timeout": 25}))
    key = Path(cfg["validator_key_file"]).expanduser().read_text().strip()
    acct = Account.from_key(key if key.startswith("0x") else "0x" + key)

    # 1. real stamp
    s = requests.post(STAMP_API, json={"wallet": STAMP_WALLET,
        "data": f"erc8004-sepolia-agent-{int(time.time())}", "label": "erc8004-sepolia-agent"},
        headers={"User-Agent": UA}, timeout=40).json()
    root, verify_url = s["merkle_root"], s["verify_url"]
    print(f"stamp merkle_root={root}\nverify_url={verify_url}")

    contract = w3.eth.contract(address=Web3.to_checksum_address(cfg["validation_registry"]), abi=abi)
    request_hash = Web3.keccak(text=f"work:{root}")
    tx = contract.functions.validationRequest(
        acct.address, args.agent_id, verify_url, request_hash
    ).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": w3.eth.chain_id, "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
        "maxFeePerGas": int(w3.eth.get_block("latest")["baseFeePerGas"]) * 2 + w3.to_wei(2, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    txh = w3.eth.send_raw_transaction(raw)
    print(f"validationRequest tx: https://sepolia.etherscan.io/tx/0x{txh.hex().removeprefix('0x')}")
    rcpt = w3.eth.wait_for_transaction_receipt(txh, timeout=300)
    print(f"status={rcpt.status} block={rcpt.blockNumber} requestHash=0x{request_hash.hex().removeprefix('0x')}")
    print(f"agentId={args.agent_id}")
    print("NEXT: /Users/colinwinter/neo_env/bin/python3 erc8004_relayer.py --once")

if __name__ == "__main__":
    main()

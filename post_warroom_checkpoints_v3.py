#!/usr/bin/env python3
"""Post 4 War Room checkpoints to ValidationRegistry on Sepolia. v3: Fixed gas limit."""

import os
import time
from web3 import Web3
from eth_account import Account

w3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia-rpc.publicnode.com"))
print(f"Connected: {w3.is_connected()}")

validation_addr = "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1"
pk = os.environ["CROSSMIND_PK"]
account = Account.from_key(pk)
agent_id = 12
chain_id = w3.eth.chain_id

balance = w3.eth.get_balance(account.address)
print(f"Wallet: {account.address}")
print(f"ETH Balance: {w3.from_wei(balance, 'ether')} ETH")
print(f"Chain ID: {chain_id}")

val_abi = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "checkpointHash", "type": "bytes32"},
            {"name": "score", "type": "uint8"},
            {"name": "proofType", "type": "uint8"},
            {"name": "proof", "type": "bytes"},
            {"name": "notes", "type": "string"}
        ],
        "name": "postAttestation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getAverageValidationScore",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

contract = w3.eth.contract(address=validation_addr, abi=val_abi)

checkpoints = [
    (91, "Terra/LUNA Collapse (-54%): SURVIVED. 7 trades, 14 refusals, max DD 2.0%. Risk manager blocked 14 unsafe trades during worst crypto crash of 2022"),
    (93, "FTX Collapse (-30%): SURVIVED with +$49 PROFIT. 6 trades, 0 refusals needed. Mean reversion captured volatility bounce despite 30% market drop"),
    (88, "COVID Black Swan (-54%): SURVIVED. 6 trades, 8 refusals, max DD 2.9%. Consecutive loss pause activated correctly, preventing further losses during historic crash"),
    (94, "FINAL WAR ROOM: 9/9 scenarios survived (incl. -54% Terra/LUNA, -54% COVID, -43% Year-End Selloff). 33 trades, 38 refusals. Max drawdown 2.9% across ALL scenarios. 100% survival rate."),
]

gas_price = int(w3.eth.gas_price * 1.5)
print(f"Gas price: {w3.from_wei(gas_price, 'gwei')} gwei")

nonce = w3.eth.get_transaction_count(account.address)
print(f"Starting nonce: {nonce}\n")

tx_results = []

for i, (score, notes) in enumerate(checkpoints):
    print(f"{'='*70}")
    print(f"[{i+1}/4] Score={score} | {notes[:70]}...")

    checkpoint_hash = Web3.keccak(text=notes)
    proof = Web3.keccak(text=f"warroom-checkpoint-{i+1}-{notes[:40]}")

    # Estimate gas first
    try:
        est_gas = contract.functions.postAttestation(
            agent_id, checkpoint_hash, score, 1, proof, notes
        ).estimate_gas({"from": account.address})
        gas_limit = int(est_gas * 1.2)  # 20% buffer
        print(f"  Est gas: {est_gas}, using: {gas_limit}")
    except Exception as e:
        print(f"  Gas estimation failed: {e}")
        gas_limit = 500000
        print(f"  Using fallback gas limit: {gas_limit}")

    tx = contract.functions.postAttestation(
        agent_id, checkpoint_hash, score, 1, proof, notes
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "chainId": chain_id,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX: 0x{tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    status = "SUCCESS" if receipt["status"] == 1 else "FAILED"
    print(f"  Block: {receipt['blockNumber']} | Gas: {receipt['gasUsed']} | {status}")

    tx_results.append({
        "idx": i + 1,
        "score": score,
        "tx": f"0x{tx_hash.hex()}",
        "block": receipt["blockNumber"],
        "status": status,
        "gas_used": receipt["gasUsed"],
    })

    if receipt["status"] != 1:
        print("  *** REVERTED ***")

    nonce += 1
    time.sleep(1)

# ── Query average score ──────────────────────────────────────────────────
print(f"\n{'='*70}")
try:
    avg_score = contract.functions.getAverageValidationScore(agent_id).call()
    print(f"getAverageValidationScore(12) = {avg_score}")
except Exception as e:
    print(f"Error: {e}")

# ── Final balance ────────────────────────────────────────────────────────
final_balance = w3.eth.get_balance(account.address)
print(f"\nWallet ETH Balance: {w3.from_wei(final_balance, 'ether')} ETH")
print(f"Gas spent this run: {w3.from_wei(balance - final_balance, 'ether')} ETH")

# ── Summary table ────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("RESULTS:")
for r in tx_results:
    print(f"  #{r['idx']}: Score {r['score']} | {r['status']} | Block {r['block']} | Gas {r['gas_used']}")
    print(f"         TX: {r['tx']}")
print()

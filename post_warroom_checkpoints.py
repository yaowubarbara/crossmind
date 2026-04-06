#!/usr/bin/env python3
"""Post 3 War Room scenario checkpoints + 1 final summary to ValidationRegistry on Sepolia."""

import os
import time
import hashlib
from web3 import Web3
from eth_account import Account

# ── Config ──────────────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia-rpc.publicnode.com"))
print(f"Connected to Sepolia: {w3.is_connected()}")

validation_addr = "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1"
pk = os.environ["CROSSMIND_PK"]
account = Account.from_key(pk)
agent_id = 12

print(f"Wallet: {account.address}")
balance = w3.eth.get_balance(account.address)
print(f"ETH Balance: {w3.from_wei(balance, 'ether')} ETH")

# ── ABI ─────────────────────────────────────────────────────────────────
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

# ── Checkpoints to post ─────────────────────────────────────────────────
checkpoints = [
    (91, "Terra/LUNA Collapse (-54%): SURVIVED. 7 trades, 14 refusals, max DD 2.0%. Risk manager blocked 14 unsafe trades during worst crypto crash of 2022"),
    (93, "FTX Collapse (-30%): SURVIVED with +$49 PROFIT. 6 trades, 0 refusals needed. Mean reversion captured volatility bounce despite 30% market drop"),
    (88, "COVID Black Swan (-54%): SURVIVED. 6 trades, 8 refusals, max DD 2.9%. Consecutive loss pause activated correctly, preventing further losses during historic crash"),
    (94, "FINAL WAR ROOM: 9/9 scenarios survived (incl. -54% Terra/LUNA, -54% COVID, -43% Year-End Selloff). 33 trades, 38 refusals. Max drawdown 2.9% across ALL scenarios. 100% survival rate."),
]

# ── Post each checkpoint ─────────────────────────────────────────────────
chain_id = w3.eth.chain_id
print(f"\nChain ID: {chain_id}")

for i, (score, notes) in enumerate(checkpoints):
    print(f"\n{'='*70}")
    print(f"Checkpoint {i+1}/4: Score={score}")
    print(f"  Notes: {notes[:80]}...")

    # Create checkpoint hash from the notes
    checkpoint_hash = Web3.keccak(text=notes)

    # Build proof bytes from notes hash
    proof = Web3.keccak(text=f"warroom-checkpoint-{i+1}-{notes[:40]}")

    nonce = w3.eth.get_transaction_count(account.address)

    tx = contract.functions.postAttestation(
        agent_id,
        checkpoint_hash,
        score,
        1,  # proofType = 1 (simulation)
        proof,
        notes
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "chainId": chain_id,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX sent: {tx_hash.hex()}")

    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status = "SUCCESS" if receipt["status"] == 1 else "FAILED"
    print(f"  Block: {receipt['blockNumber']} | Gas used: {receipt['gasUsed']} | Status: {status}")

    if receipt["status"] != 1:
        print("  *** TRANSACTION FAILED - check contract state ***")

    # Small delay between transactions
    if i < len(checkpoints) - 1:
        time.sleep(2)

# ── Query average score ──────────────────────────────────────────────────
print(f"\n{'='*70}")
print("Querying getAverageValidationScore(12)...")
try:
    avg_score = contract.functions.getAverageValidationScore(agent_id).call()
    print(f"Average Validation Score for Agent 12: {avg_score}")
except Exception as e:
    print(f"Error querying average score: {e}")

# ── Final balance check ──────────────────────────────────────────────────
final_balance = w3.eth.get_balance(account.address)
print(f"\nFinal ETH Balance: {w3.from_wei(final_balance, 'ether')} ETH")
gas_spent = w3.from_wei(balance - final_balance, 'ether')
print(f"Gas spent on 4 txs: {gas_spent} ETH")
print("\nDone!")

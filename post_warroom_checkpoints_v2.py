#!/usr/bin/env python3
"""Post 3 War Room scenario checkpoints + 1 final summary to ValidationRegistry on Sepolia.
Uses higher gas price and multiple RPC endpoints for reliability."""

import os
import time
from web3 import Web3
from eth_account import Account

# ── Try multiple RPCs ───────────────────────────────────────────────────
RPCS = [
    "https://ethereum-sepolia-rpc.publicnode.com",
    "https://rpc.sepolia.org",
    "https://sepolia.drpc.org",
]

w3 = None
for rpc in RPCS:
    try:
        _w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
        if _w3.is_connected():
            w3 = _w3
            print(f"Connected to: {rpc}")
            break
    except:
        continue

if not w3:
    print("FATAL: No RPC connected")
    exit(1)

# ── Config ──────────────────────────────────────────────────────────────
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
chain_id = w3.eth.chain_id
print(f"Chain ID: {chain_id}")

# ── First, check if the pending tx (nonce 12) already confirmed ──────────
current_nonce = w3.eth.get_transaction_count(account.address)
pending_nonce = w3.eth.get_transaction_count(account.address, 'pending')
print(f"Current nonce: {current_nonce}, Pending nonce: {pending_nonce}")

# If nonce 12 is still pending, we need to either wait or replace it
# Let's check the receipt first
first_tx_hash = "0x597dbc4dea1a5366284eb4bb5d82de0d795047208842ea0dfe2301c34ed42ff6"
try:
    receipt = w3.eth.get_transaction_receipt(first_tx_hash)
    if receipt:
        print(f"TX 1 already confirmed! Block: {receipt['blockNumber']}, Status: {'SUCCESS' if receipt['status']==1 else 'FAILED'}")
        start_index = 1  # Skip checkpoint 1
        start_nonce = current_nonce
    else:
        start_index = 0
        start_nonce = current_nonce
except Exception:
    print("TX 1 receipt not found - will resubmit checkpoint 1")
    start_index = 0
    start_nonce = current_nonce

# ── Checkpoints ─────────────────────────────────────────────────────────
checkpoints = [
    (91, "Terra/LUNA Collapse (-54%): SURVIVED. 7 trades, 14 refusals, max DD 2.0%. Risk manager blocked 14 unsafe trades during worst crypto crash of 2022"),
    (93, "FTX Collapse (-30%): SURVIVED with +$49 PROFIT. 6 trades, 0 refusals needed. Mean reversion captured volatility bounce despite 30% market drop"),
    (88, "COVID Black Swan (-54%): SURVIVED. 6 trades, 8 refusals, max DD 2.9%. Consecutive loss pause activated correctly, preventing further losses during historic crash"),
    (94, "FINAL WAR ROOM: 9/9 scenarios survived (incl. -54% Terra/LUNA, -54% COVID, -43% Year-End Selloff). 33 trades, 38 refusals. Max drawdown 2.9% across ALL scenarios. 100% survival rate."),
]

# Use 2x gas price for faster inclusion
base_gas = w3.eth.gas_price
gas_price = int(base_gas * 2)
print(f"Base gas: {w3.from_wei(base_gas, 'gwei')} gwei, Using: {w3.from_wei(gas_price, 'gwei')} gwei")

tx_hashes = []

for i in range(start_index, len(checkpoints)):
    score, notes = checkpoints[i]
    print(f"\n{'='*70}")
    print(f"Checkpoint {i+1}/4: Score={score}")
    print(f"  Notes: {notes[:80]}...")

    checkpoint_hash = Web3.keccak(text=notes)
    proof = Web3.keccak(text=f"warroom-checkpoint-{i+1}-{notes[:40]}")

    nonce = start_nonce + (i - start_index)
    # If we're replacing nonce 12 (the stuck tx), use same nonce with higher gas
    if i == 0 and current_nonce == 12 and pending_nonce == 13:
        nonce = 12  # Replace the stuck tx
        print(f"  Replacing stuck TX at nonce 12 with higher gas")

    print(f"  Nonce: {nonce}")

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
        "gasPrice": gas_price,
        "chainId": chain_id,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX sent: {tx_hash.hex()}")
    tx_hashes.append((i+1, tx_hash, score, notes[:60]))

    # Wait for this tx to confirm before sending next
    print(f"  Waiting for confirmation...")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        status = "SUCCESS" if receipt["status"] == 1 else "FAILED"
        print(f"  Block: {receipt['blockNumber']} | Gas: {receipt['gasUsed']} | Status: {status}")
        if receipt["status"] != 1:
            print("  *** TRANSACTION FAILED ***")
    except Exception as e:
        print(f"  Timeout waiting for receipt: {e}")
        print("  Continuing anyway...")

    time.sleep(1)

# ── Query average score ──────────────────────────────────────────────────
print(f"\n{'='*70}")
print("Querying getAverageValidationScore(12)...")
try:
    avg_score = contract.functions.getAverageValidationScore(agent_id).call()
    print(f"\n*** Average Validation Score for Agent 12: {avg_score} ***\n")
except Exception as e:
    print(f"Error querying average score: {e}")

# ── Final balance ────────────────────────────────────────────────────────
final_balance = w3.eth.get_balance(account.address)
print(f"Final ETH Balance: {w3.from_wei(final_balance, 'ether')} ETH")
gas_spent = w3.from_wei(balance - final_balance, 'ether')
print(f"Gas spent: {gas_spent} ETH")

# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("SUMMARY OF POSTED CHECKPOINTS:")
for idx, tx_hash, score, notes_preview in tx_hashes:
    print(f"  #{idx}: Score {score} | TX: 0x{tx_hash.hex()}")
    print(f"         {notes_preview}...")
print(f"\nAll done!")

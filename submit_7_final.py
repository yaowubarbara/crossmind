#!/usr/bin/env python3
"""Submit 7 TradeIntents to RiskRouter on Ethereum Sepolia.
Each TX: get nonce, build intent, sign EIP-712, submit, wait for receipt."""

import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data
import time

# --- Config ---
w3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia-rpc.publicnode.com"))
pk = os.environ["CROSSMIND_PK"]
account = Account.from_key(pk)
agent_id = 12
router_addr = "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC"

router_abi = [{
    "inputs": [
        {"name": "intent", "type": "tuple", "components": [
            {"name": "agentId", "type": "uint256"},
            {"name": "agentWallet", "type": "address"},
            {"name": "pair", "type": "string"},
            {"name": "action", "type": "string"},
            {"name": "amountUsdScaled", "type": "uint256"},
            {"name": "maxSlippageBps", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "deadline", "type": "uint256"},
        ]},
        {"name": "signature", "type": "bytes"},
    ],
    "name": "submitTradeIntent",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function",
}, {
    "inputs": [{"name": "agentId", "type": "uint256"}],
    "name": "getIntentNonce",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function",
}]

router = w3.eth.contract(address=router_addr, abi=router_abi)

domain = {
    "name": "RiskRouter",
    "version": "1",
    "chainId": 11155111,
    "verifyingContract": router_addr,
}
types = {
    "TradeIntent": [
        {"name": "agentId", "type": "uint256"},
        {"name": "agentWallet", "type": "address"},
        {"name": "pair", "type": "string"},
        {"name": "action", "type": "string"},
        {"name": "amountUsdScaled", "type": "uint256"},
        {"name": "maxSlippageBps", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "deadline", "type": "uint256"},
    ]
}

# --- 7 trades to submit ---
trades = [
    ("SELL", "XBTUSD", 400),
    ("BUY",  "ETHUSD", 250),
    ("BUY",  "XBTUSD", 300),
    ("SELL", "SOLUSD", 150),
    ("BUY",  "ETHUSD", 500),
    ("SELL", "XBTUSD", 200),
    ("BUY",  "SOLUSD", 350),
]

print(f"Wallet:     {account.address}")
print(f"RiskRouter: {router_addr}")
print(f"Chain:      Sepolia (11155111)")
bal_start = w3.eth.get_balance(account.address)
print(f"Starting ETH balance: {w3.from_wei(bal_start, 'ether'):.6f} ETH")
contract_nonce = router.functions.getIntentNonce(agent_id).call()
print(f"Contract nonce (agent {agent_id}): {contract_nonce}")
print(f"{'=' * 70}")

# First, handle the stuck pending TX (nonce 22) by replacing it with a higher gas price
pending_nonce = w3.eth.get_transaction_count(account.address, "pending")
confirmed_nonce = w3.eth.get_transaction_count(account.address, "latest")
if pending_nonce > confirmed_nonce:
    print(f"\nClearing {pending_nonce - confirmed_nonce} stuck pending TX(s)...")
    for stuck_nonce in range(confirmed_nonce, pending_nonce):
        # Send a self-transfer to replace the stuck TX
        gas_price = int(w3.eth.gas_price * 3)  # 3x gas to ensure replacement
        cancel_tx = {
            "from": account.address,
            "to": account.address,
            "value": 0,
            "nonce": stuck_nonce,
            "gasPrice": gas_price,
            "gas": 21000,
            "chainId": 11155111,
        }
        signed_cancel = account.sign_transaction(cancel_tx)
        try:
            tx_hash = w3.eth.send_raw_transaction(signed_cancel.raw_transaction)
            print(f"  Replacement TX for nonce {stuck_nonce}: 0x{tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"  Cleared! (block {receipt['blockNumber']})")
        except Exception as e:
            if "already known" in str(e).lower() or "nonce too low" in str(e).lower():
                print(f"  Nonce {stuck_nonce}: already processed or replaced")
            else:
                print(f"  Error clearing nonce {stuck_nonce}: {e}")
                # Wait and check if it resolved
                time.sleep(10)
    print()

success_count = 0
tx_results = []

for i, (action, pair, amount_usd) in enumerate(trades, start=1):
    print(f"\n--- Trade {i}/7: {action} {pair} ${amount_usd} ---")

    # 1. Get current nonce from contract
    contract_nonce = router.functions.getIntentNonce(agent_id).call()
    print(f"  Contract nonce: {contract_nonce}")

    # 2. Build intent
    deadline = int(time.time()) + 600
    amount_scaled = amount_usd * 10**18
    slippage_bps = 50

    intent_data = {
        "agentId": agent_id,
        "agentWallet": account.address,
        "pair": pair,
        "action": action,
        "amountUsdScaled": amount_scaled,
        "maxSlippageBps": slippage_bps,
        "nonce": contract_nonce,
        "deadline": deadline,
    }

    # 3. Sign EIP-712
    full_message = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            **types,
        },
        "primaryType": "TradeIntent",
        "domain": domain,
        "message": intent_data,
    }

    signable = encode_typed_data(full_message=full_message)
    signed = account.sign_message(signable)
    signature = signed.signature

    # 4. Build and send transaction
    intent_tuple = (
        intent_data["agentId"],
        intent_data["agentWallet"],
        intent_data["pair"],
        intent_data["action"],
        intent_data["amountUsdScaled"],
        intent_data["maxSlippageBps"],
        intent_data["nonce"],
        intent_data["deadline"],
    )

    tx_nonce = w3.eth.get_transaction_count(account.address, "latest")
    gas_price = int(w3.eth.gas_price * 1.5)

    tx = router.functions.submitTradeIntent(
        intent_tuple, signature
    ).build_transaction({
        "from": account.address,
        "nonce": tx_nonce,
        "gasPrice": gas_price,
        "chainId": 11155111,
    })

    try:
        gas_est = w3.eth.estimate_gas(tx)
        tx["gas"] = int(gas_est * 1.3)
    except Exception as e:
        print(f"  Gas estimation failed: {e}")
        tx["gas"] = 300000

    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"  TX hash: 0x{tx_hash.hex()}")

    # 5. Wait for receipt
    print(f"  Waiting for confirmation...", end="", flush=True)
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        status = "SUCCESS" if receipt["status"] == 1 else "REVERTED"
        gas_used = receipt["gasUsed"]
        block = receipt["blockNumber"]
        print(f" {status} (block {block}, gas {gas_used})")

        if receipt["status"] == 1:
            success_count += 1
            tx_results.append((i, action, pair, amount_usd, "SUCCESS", f"0x{tx_hash.hex()}", block))
        else:
            tx_results.append((i, action, pair, amount_usd, "REVERTED", f"0x{tx_hash.hex()}", block))
    except Exception as e:
        print(f" ERROR: {e}")
        tx_results.append((i, action, pair, amount_usd, "TIMEOUT", f"0x{tx_hash.hex()}", None))

    # 6. Delay between trades
    if i < 7:
        print(f"  Waiting 2 seconds...")
        time.sleep(2)

# --- Summary ---
print(f"\n{'=' * 70}")
print(f"TRADE SUBMISSION RESULTS")
print(f"{'=' * 70}")
print(f"{'#':<4} {'Action':<6} {'Pair':<10} {'Amount':<8} {'Status':<10} {'Block':<12} TX Hash")
print(f"{'-'*4} {'-'*6} {'-'*10} {'-'*8} {'-'*10} {'-'*12} {'-'*40}")
for (num, action, pair, amt, status, tx_h, block) in tx_results:
    block_str = str(block) if block else "N/A"
    print(f"{num:<4} {action:<6} {pair:<10} ${amt:<7} {status:<10} {block_str:<12} {tx_h[:22]}...")

bal_end = w3.eth.get_balance(account.address)
gas_spent = bal_start - bal_end
final_nonce = router.functions.getIntentNonce(agent_id).call()

print(f"\n{'=' * 70}")
print(f"Trades submitted (TX success): {success_count}/7")
print(f"Previous intents: 3  |  New intents: {success_count}  |  Total: {3 + success_count}")
print(f"Contract nonce (agent {agent_id}): {final_nonce}")
print(f"ETH spent on gas: {w3.from_wei(gas_spent, 'ether'):.6f} ETH")
print(f"Remaining ETH balance: {w3.from_wei(bal_end, 'ether'):.6f} ETH")

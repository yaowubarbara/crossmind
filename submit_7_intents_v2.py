#!/usr/bin/env python3
"""Submit 7 TradeIntents to RiskRouter on Ethereum Sepolia.
Waits for each tx confirmation before sending the next to avoid nonce issues."""

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

print(f"Wallet: {account.address}")
print(f"RiskRouter: {router_addr}")
print(f"Chain: Sepolia (11155111)")
bal_start = w3.eth.get_balance(account.address)
print(f"Starting ETH balance: {w3.from_wei(bal_start, 'ether'):.6f} ETH")

# Check starting nonce
start_nonce = router.functions.getIntentNonce(agent_id).call()
print(f"Starting contract nonce for agent {agent_id}: {start_nonce}")
print(f"=" * 70)

success_count = 0

for i, (action, pair, amount_usd) in enumerate(trades, start=1):
    print(f"\n--- Trade {i}/7: {action} {pair} ${amount_usd} ---")

    # 1. Get current nonce from contract (fresh read each time after confirmation)
    contract_nonce = router.functions.getIntentNonce(agent_id).call()
    print(f"  Contract nonce: {contract_nonce}")

    # 2. Build intent
    deadline = int(time.time()) + 600  # 10 min from now
    amount_scaled = amount_usd * 10**18
    slippage_bps = 50  # 0.5%

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

    tx_nonce = w3.eth.get_transaction_count(account.address)
    # Use slightly higher gas price to help with Sepolia congestion
    gas_price = int(w3.eth.gas_price * 1.5)

    tx = router.functions.submitTradeIntent(
        intent_tuple, signature
    ).build_transaction({
        "from": account.address,
        "nonce": tx_nonce,
        "gasPrice": gas_price,
        "chainId": 11155111,
    })

    # Estimate gas
    try:
        gas_est = w3.eth.estimate_gas(tx)
        tx["gas"] = int(gas_est * 1.3)
    except Exception as e:
        print(f"  Gas estimation failed: {e}")
        print(f"  Using default gas limit 300000")
        tx["gas"] = 300000

    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"  TX hash: 0x{tx_hash.hex()}")

    # 5. Wait for receipt with longer timeout for Sepolia
    print(f"  Waiting for confirmation...", end="", flush=True)
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        status = "SUCCESS" if receipt["status"] == 1 else "REVERTED"
        print(f" {status} (block {receipt['blockNumber']}, gas used {receipt['gasUsed']})")

        if receipt["status"] == 1:
            success_count += 1
        else:
            print(f"  WARNING: Transaction reverted!")
    except Exception as e:
        print(f" TIMEOUT/ERROR: {e}")
        # Still wait a bit and check if it got mined
        time.sleep(5)

    # 6. Delay between trades to let Sepolia catch up
    if i < 7:
        print(f"  Waiting 4 seconds before next trade...")
        time.sleep(4)

# --- Summary ---
print(f"\n{'=' * 70}")
print(f"SUMMARY")
print(f"{'=' * 70}")
bal_end = w3.eth.get_balance(account.address)
gas_spent = bal_start - bal_end
print(f"Trades submitted successfully: {success_count}/7")
print(f"Total trades on contract (target): {start_nonce + success_count} (was {start_nonce} + {success_count} new)")
print(f"ETH spent on gas: {w3.from_wei(gas_spent, 'ether'):.6f} ETH")
print(f"Remaining ETH balance: {w3.from_wei(bal_end, 'ether'):.6f} ETH")

# Verify final nonce
final_nonce = router.functions.getIntentNonce(agent_id).call()
print(f"Final contract nonce for agent {agent_id}: {final_nonce}")

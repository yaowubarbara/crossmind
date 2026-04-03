"""
CrossMind ERC-8004 Agent Registration on Base Sepolia.

Registers CrossMind as a trustless agent on the ERC-8004 Identity Registry.
Uses Base Sepolia testnet.

Usage:
    python register_8004.py --private-key 0x...
"""

import argparse
import json
import base64
from web3 import Web3

# Base Sepolia config
BASE_SEPOLIA_RPC = "https://sepolia.base.org"
CHAIN_ID = 84532

# ERC-8004 Identity Registry on Base Sepolia
# Note: Using the same contract address as mainnet — if not deployed on Base Sepolia,
# we'll deploy our own minimal registry or use the mainnet address
IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

REGISTER_ABI = [
    {
        "inputs": [{"name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# CrossMind agent metadata
AGENT_METADATA = {
    "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
    "name": "CrossMind",
    "description": (
        "Red-teamed transparent trading agent that proves when refusing to trade "
        "protects capital. War Room stress-tested against 6 real market crashes. "
        "Every decision is recorded in a SHA-256 hash-chained Trust Ledger."
    ),
    "image": "",
    "active": True,
    "x402Support": False,
    "services": [
        {"name": "web", "endpoint": "https://github.com/yaowubarbara/crossmind"},
    ],
    "capabilities": [
        "autonomous-trading",
        "risk-management",
        "refusal-proof-generation",
        "adversarial-stress-testing",
        "trust-ledger-verification",
    ],
    "validationArtifacts": {
        "trustLedger": {
            "format": "JSONL",
            "hashAlgorithm": "SHA-256",
            "chainVerification": True,
        },
        "warRoom": {
            "scenarios": 6,
            "survived": 6,
            "maxDrawdown": "1.9%",
        },
    },
}


def main():
    parser = argparse.ArgumentParser(description="Register CrossMind on ERC-8004")
    parser.add_argument("--private-key", required=True, help="Wallet private key (0x...)")
    parser.add_argument("--rpc", default=BASE_SEPOLIA_RPC, help="RPC URL")
    parser.add_argument("--registry", default=IDENTITY_REGISTRY, help="Registry contract address")
    args = parser.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        print("ERROR: Cannot connect to RPC")
        return

    account = w3.eth.account.from_key(args.private_key)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")

    print()
    print("  CROSSMIND // ERC-8004 REGISTRATION")
    print("  " + "=" * 45)
    print(f"  Network:   Base Sepolia (Chain {CHAIN_ID})")
    print(f"  Registry:  {args.registry}")
    print(f"  Wallet:    {account.address}")
    print(f"  Balance:   {balance_eth:.4f} ETH")
    print()

    if balance_eth < 0.001:
        print("  ERROR: Need at least 0.001 ETH for gas")
        return

    # Encode agent metadata as base64 data URI
    json_str = json.dumps(AGENT_METADATA)
    b64 = base64.b64encode(json_str.encode()).decode()
    agent_uri = f"data:application/json;base64,{b64}"

    print(f"  Agent:     {AGENT_METADATA['name']}")
    print(f"  URI size:  {len(agent_uri)} bytes")
    print()

    # Check if registry contract exists
    code = w3.eth.get_code(Web3.to_checksum_address(args.registry))
    if code == b"" or code == b"0x":
        print("  WARNING: No contract found at registry address on this network.")
        print("  The ERC-8004 registry may not be deployed on Base Sepolia.")
        print()
        print("  Saving registration data locally instead...")
        save_local_registration(account.address, agent_uri)
        return

    # Build transaction
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(args.registry),
        abi=REGISTER_ABI,
    )

    print("  Estimating gas...")
    try:
        gas_estimate = contract.functions.register(agent_uri).estimate_gas(
            {"from": account.address}
        )
        print(f"  Gas estimate: {gas_estimate:,}")
    except Exception as e:
        print(f"  Gas estimation failed: {e}")
        print("  Saving registration data locally instead...")
        save_local_registration(account.address, agent_uri)
        return

    # Send transaction
    print("  Sending registration transaction...")
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.register(agent_uri).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": gas_estimate + 50000,
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "maxFeePerGas": w3.eth.gas_price + w3.to_wei(2, "gwei"),
        "chainId": CHAIN_ID,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX: https://sepolia.basescan.org/tx/{tx_hash.hex()}")

    print("  Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt["status"] == 1:
        print()
        print("  REGISTRATION SUCCESSFUL")
        print("  " + "=" * 45)
        print(f"  TX Hash:   {tx_hash.hex()}")
        print(f"  Gas Used:  {receipt['gasUsed']:,}")
        print(f"  Block:     {receipt['blockNumber']}")
        print()

        # Save proof
        proof = {
            "agent": "CrossMind",
            "wallet": account.address,
            "registry": args.registry,
            "chain": "base-sepolia",
            "chainId": CHAIN_ID,
            "txHash": tx_hash.hex(),
            "blockNumber": receipt["blockNumber"],
            "gasUsed": receipt["gasUsed"],
            "timestamp": str(w3.eth.get_block(receipt["blockNumber"])["timestamp"]),
        }
        with open("evidence/erc8004_registration.json", "w") as f:
            json.dump(proof, f, indent=2)
        print("  Proof saved to evidence/erc8004_registration.json")
    else:
        print("  TRANSACTION REVERTED")


def save_local_registration(address, agent_uri):
    """Save registration data locally when on-chain registration isn't available."""
    import os
    os.makedirs("evidence", exist_ok=True)
    reg_data = {
        "agent": "CrossMind",
        "wallet": address,
        "agentURI": agent_uri,
        "metadata": AGENT_METADATA,
        "status": "pending-on-chain",
        "targetRegistry": IDENTITY_REGISTRY,
        "targetChain": "base-sepolia",
        "note": "Registration data prepared. On-chain registration pending deployment of ERC-8004 registry on Base Sepolia.",
    }
    with open("evidence/erc8004_registration_pending.json", "w") as f:
        json.dump(reg_data, f, indent=2)
    print("  Saved to evidence/erc8004_registration_pending.json")
    print()
    print("  Agent card also available at .well-known/agent.json")


if __name__ == "__main__":
    main()

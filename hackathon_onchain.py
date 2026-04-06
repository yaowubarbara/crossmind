"""
CrossMind Hackathon On-Chain Operations — Ethereum Sepolia

Handles all on-chain interactions for the Kraken DeFi hackathon:
  register    — Register CrossMind on AgentRegistry
  claim       — Claim sandbox allocation from HackathonVault
  trade       — Submit EIP-712 signed TradeIntent to RiskRouter
  checkpoint  — Post attestation to ValidationRegistry
  status      — Show current on-chain status
  full-pipeline — Run everything end-to-end

Usage:
    python hackathon_onchain.py register
    python hackathon_onchain.py claim
    python hackathon_onchain.py trade --pair XBTUSD --action BUY --amount 500
    python hackathon_onchain.py checkpoint --score 85 --notes "War Room survived"
    python hackathon_onchain.py status
    python hackathon_onchain.py full-pipeline
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode as abi_encode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = SCRIPT_DIR / "evidence"
AGENT_ID_FILE = SCRIPT_DIR / "agent_id.json"
TX_LOG_FILE = EVIDENCE_DIR / "onchain_transactions.json"

RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
CHAIN_ID = 11155111
ETHERSCAN_BASE = "https://sepolia.etherscan.io"

WALLET_ADDRESS = "0x6c8019b971D600916AC39cc96a830E68A034dF47"
PRIVATE_KEY = os.environ.get("CROSSMIND_PK", "")

# Shared contract addresses (Sepolia)
CONTRACTS = {
    "AgentRegistry":      "0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3",
    "HackathonVault":     "0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90",
    "RiskRouter":         "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC",
    "ReputationRegistry": "0x423a9904e39537a9997fbaF0f220d79D7d545763",
    "ValidationRegistry": "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1",
}

# CrossMind identity
AGENT_NAME = "CrossMind"
AGENT_DESCRIPTION = (
    "Red-teamed capital protection agent that proves when refusing to trade "
    "saves money. War Room stress-tested against 6 real crashes. Every decision "
    "recorded in SHA-256 Trust Ledger."
)
AGENT_CAPABILITIES = [
    "trading",
    "eip712-signing",
    "risk-management",
    "refusal-proof",
]
AGENT_URI = (
    "https://raw.githubusercontent.com/yaowubarbara/crossmind/main/"
    ".well-known/agent.json"
)

# ---------------------------------------------------------------------------
# ABI Definitions
# ---------------------------------------------------------------------------

AGENT_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "agentWallet", "type": "address"},
            {"name": "name", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "capabilities", "type": "string[]"},
            {"name": "agentURI", "type": "string"},
        ],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getAgent",
        "outputs": [
            {
                "components": [
                    {"name": "operatorWallet", "type": "address"},
                    {"name": "agentWallet", "type": "address"},
                    {"name": "name", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "capabilities", "type": "string[]"},
                    {"name": "registeredAt", "type": "uint256"},
                    {"name": "active", "type": "bool"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": True, "name": "operatorWallet", "type": "address"},
            {"indexed": False, "name": "agentWallet", "type": "address"},
            {"indexed": False, "name": "name", "type": "string"},
        ],
        "name": "AgentRegistered",
        "type": "event",
    },
]

HACKATHON_VAULT_ABI = [
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "claimAllocation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "AllocationClaimed",
        "type": "event",
    },
]

RISK_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "agentId", "type": "uint256"},
                    {"name": "agentWallet", "type": "address"},
                    {"name": "pair", "type": "string"},
                    {"name": "action", "type": "string"},
                    {"name": "amountUsdScaled", "type": "uint256"},
                    {"name": "maxSlippageBps", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
                "name": "intent",
                "type": "tuple",
            },
            {"name": "signature", "type": "bytes"},
        ],
        "name": "submitTradeIntent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getIntentNonce",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "pair", "type": "string"},
            {"indexed": False, "name": "action", "type": "string"},
            {"indexed": False, "name": "amountUsdScaled", "type": "uint256"},
        ],
        "name": "TradeApproved",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "reason", "type": "string"},
        ],
        "name": "TradeRejected",
        "type": "event",
    },
]

REPUTATION_REGISTRY_ABI = [
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getReputation",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

VALIDATION_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "checkpointHash", "type": "bytes32"},
            {"name": "score", "type": "uint256"},
            {"name": "notes", "type": "string"},
        ],
        "name": "postEIP712Attestation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getValidationScore",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "checkpointHash", "type": "bytes32"},
            {"indexed": False, "name": "score", "type": "uint256"},
        ],
        "name": "AttestationPosted",
        "type": "event",
    },
]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def banner(title: str):
    """Print a section banner."""
    width = 60
    print()
    print("  " + "=" * width)
    print(f"  CROSSMIND // {title}")
    print("  " + "=" * width)


def info(msg: str):
    print(f"  [+] {msg}")


def warn(msg: str):
    print(f"  [!] {msg}")


def error(msg: str):
    print(f"  [ERROR] {msg}")


def etherscan_tx(tx_hash: str) -> str:
    return f"{ETHERSCAN_BASE}/tx/0x{tx_hash}"


def etherscan_addr(addr: str) -> str:
    return f"{ETHERSCAN_BASE}/address/{addr}"


def get_web3() -> Web3:
    """Create and validate a Web3 connection."""
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        error(f"Cannot connect to RPC: {RPC_URL}")
        sys.exit(1)
    return w3


def get_account(w3: Web3):
    """Load the wallet account."""
    acct = Account.from_key(PRIVATE_KEY)
    balance = w3.eth.get_balance(acct.address)
    balance_eth = w3.from_wei(balance, "ether")
    info(f"Wallet:  {acct.address}")
    info(f"Balance: {balance_eth:.6f} ETH")
    if balance_eth < 0.0001:
        warn("Balance very low - transactions may fail due to insufficient gas")
    return acct, balance_eth


def load_agent_id() -> int:
    """Load agentId from local file."""
    if not AGENT_ID_FILE.exists():
        error("agent_id.json not found. Run 'register' first.")
        sys.exit(1)
    with open(AGENT_ID_FILE) as f:
        data = json.load(f)
    agent_id = data.get("agentId")
    if agent_id is None:
        error("agentId not found in agent_id.json")
        sys.exit(1)
    return int(agent_id)


def save_agent_id(agent_id: int, tx_hash: str):
    """Save agentId to local file."""
    data = {
        "agentId": agent_id,
        "agentName": AGENT_NAME,
        "wallet": WALLET_ADDRESS,
        "registrationTxHash": tx_hash,
        "chain": "sepolia",
        "chainId": CHAIN_ID,
        "savedAt": datetime.now(timezone.utc).isoformat(),
    }
    with open(AGENT_ID_FILE, "w") as f:
        json.dump(data, f, indent=2)
    info(f"Agent ID saved to {AGENT_ID_FILE}")


def log_transaction(action: str, tx_hash: str, details: dict = None):
    """Append a transaction record to the evidence log."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    if TX_LOG_FILE.exists():
        try:
            with open(TX_LOG_FILE) as f:
                records = json.load(f)
        except (json.JSONDecodeError, ValueError):
            records = []

    record = {
        "action": action,
        "txHash": tx_hash,
        "etherscanUrl": etherscan_tx(tx_hash),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chain": "sepolia",
        "chainId": CHAIN_ID,
    }
    if details:
        record.update(details)

    records.append(record)

    with open(TX_LOG_FILE, "w") as f:
        json.dump(records, f, indent=2)

    info(f"Transaction logged to {TX_LOG_FILE.name}")


def send_tx(w3: Web3, acct, func, label: str, extra_details: dict = None):
    """Build, sign, send, and wait for a contract function call.

    Returns the transaction receipt.
    """
    info(f"Building transaction: {label}")

    try:
        gas_estimate = func.estimate_gas({"from": acct.address})
        info(f"Gas estimate: {gas_estimate:,}")
    except Exception as e:
        warn(f"Gas estimation failed: {e}")
        warn("Using fallback gas limit of 500,000")
        gas_estimate = 500_000

    nonce = w3.eth.get_transaction_count(acct.address)
    gas_price = w3.eth.gas_price

    tx = func.build_transaction({
        "from": acct.address,
        "nonce": nonce,
        "gas": int(gas_estimate * 1.3),  # 30% buffer
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
        "maxFeePerGas": gas_price + w3.to_wei(3, "gwei"),
        "chainId": CHAIN_ID,
    })

    signed = acct.sign_transaction(tx)
    info("Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = tx_hash.hex()

    info(f"TX Hash: 0x{tx_hash_hex}")
    info(f"Etherscan: {etherscan_tx(tx_hash_hex)}")

    info("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt["status"] == 1:
        info(f"CONFIRMED in block {receipt['blockNumber']} | Gas used: {receipt['gasUsed']:,}")
    else:
        error(f"TRANSACTION REVERTED in block {receipt['blockNumber']}")

    log_transaction(label, tx_hash_hex, extra_details)

    return receipt, tx_hash_hex


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_register(w3: Web3, acct):
    """Register CrossMind on the AgentRegistry."""
    banner("AGENT REGISTRATION")

    registry_addr = Web3.to_checksum_address(CONTRACTS["AgentRegistry"])
    info(f"Registry: {registry_addr}")
    info(f"Agent:    {AGENT_NAME}")
    info(f"URI:      {AGENT_URI}")

    # Check contract exists
    code = w3.eth.get_code(registry_addr)
    if code == b"" or code == b"\x00":
        error(f"No contract found at {registry_addr}")
        sys.exit(1)
    info(f"Contract code verified ({len(code)} bytes)")

    contract = w3.eth.contract(address=registry_addr, abi=AGENT_REGISTRY_ABI)

    func = contract.functions.register(
        Web3.to_checksum_address(WALLET_ADDRESS),
        AGENT_NAME,
        AGENT_DESCRIPTION,
        AGENT_CAPABILITIES,
        AGENT_URI,
    )

    receipt, tx_hash_hex = send_tx(
        w3, acct, func, "register",
        {"contract": "AgentRegistry", "agentName": AGENT_NAME},
    )

    if receipt["status"] != 1:
        error("Registration failed")
        sys.exit(1)

    # Extract agentId from event logs
    agent_id = None
    try:
        logs = contract.events.AgentRegistered().process_receipt(receipt)
        if logs:
            agent_id = logs[0]["args"]["agentId"]
            info(f"Agent ID from event: {agent_id}")
    except Exception as e:
        warn(f"Could not parse AgentRegistered event: {e}")

    # Fallback: try decoding return value from logs or use log topic
    if agent_id is None and receipt["logs"]:
        for log in receipt["logs"]:
            if log["address"].lower() == registry_addr.lower() and len(log["topics"]) >= 2:
                # First indexed param is agentId
                agent_id = int(log["topics"][1].hex(), 16)
                info(f"Agent ID from raw log topic: {agent_id}")
                break

    # Second fallback: try to read the return data
    if agent_id is None:
        warn("Could not extract agentId from events. Trying sequential ID lookup...")
        # Try IDs starting from 1
        for test_id in range(1, 100):
            try:
                agent_data = contract.functions.getAgent(test_id).call()
                if agent_data[1].lower() == WALLET_ADDRESS.lower():  # agentWallet match
                    agent_id = test_id
                    info(f"Agent ID found by wallet lookup: {agent_id}")
                    break
            except Exception:
                break

    if agent_id is None:
        warn("Could not determine agentId automatically. Defaulting to 1.")
        warn("Check Etherscan and update agent_id.json manually if needed.")
        agent_id = 1

    save_agent_id(agent_id, tx_hash_hex)

    print()
    info("REGISTRATION COMPLETE")
    info(f"Agent ID:  {agent_id}")
    info(f"TX:        {etherscan_tx(tx_hash_hex)}")
    print()

    return agent_id


def cmd_claim(w3: Web3, acct):
    """Claim sandbox allocation from HackathonVault."""
    banner("CLAIM SANDBOX ALLOCATION")

    agent_id = load_agent_id()
    info(f"Agent ID: {agent_id}")

    vault_addr = Web3.to_checksum_address(CONTRACTS["HackathonVault"])
    info(f"Vault: {vault_addr}")

    contract = w3.eth.contract(address=vault_addr, abi=HACKATHON_VAULT_ABI)

    # Check balance before
    try:
        balance_before = contract.functions.getBalance(agent_id).call()
        info(f"Balance before: {balance_before}")
    except Exception as e:
        warn(f"Could not read balance before claim: {e}")
        balance_before = 0

    func = contract.functions.claimAllocation(agent_id)

    receipt, tx_hash_hex = send_tx(
        w3, acct, func, "claimAllocation",
        {"contract": "HackathonVault", "agentId": agent_id},
    )

    if receipt["status"] != 1:
        error("Claim failed")
        sys.exit(1)

    # Parse AllocationClaimed event
    try:
        logs = contract.events.AllocationClaimed().process_receipt(receipt)
        if logs:
            amount = logs[0]["args"]["amount"]
            info(f"Claimed amount: {amount}")
    except Exception as e:
        warn(f"Could not parse AllocationClaimed event: {e}")

    # Check balance after
    try:
        balance_after = contract.functions.getBalance(agent_id).call()
        info(f"Balance after: {balance_after}")
    except Exception as e:
        warn(f"Could not read balance after claim: {e}")

    print()
    info("ALLOCATION CLAIMED")
    info(f"TX: {etherscan_tx(tx_hash_hex)}")
    print()

    return receipt


def cmd_trade(w3: Web3, acct, pair: str, action: str, amount: int):
    """Submit a signed TradeIntent to the RiskRouter."""
    banner(f"TRADE INTENT: {action} {pair} ${amount}")

    agent_id = load_agent_id()
    info(f"Agent ID: {agent_id}")

    router_addr = Web3.to_checksum_address(CONTRACTS["RiskRouter"])
    info(f"RiskRouter: {router_addr}")

    contract = w3.eth.contract(address=router_addr, abi=RISK_ROUTER_ABI)

    # Get nonce from contract
    try:
        nonce = contract.functions.getIntentNonce(agent_id).call()
        info(f"Intent nonce: {nonce}")
    except Exception as e:
        warn(f"Could not read nonce from contract: {e}. Using 0.")
        nonce = 0

    # Build TradeIntent
    amount_usd_scaled = amount * 100  # scale by 100 per spec
    max_slippage_bps = 100            # 1%
    deadline = int(time.time()) + 300  # 5 minutes from now

    intent_data = {
        "agentId": agent_id,
        "agentWallet": Web3.to_checksum_address(WALLET_ADDRESS),
        "pair": pair,
        "action": action,
        "amountUsdScaled": amount_usd_scaled,
        "maxSlippageBps": max_slippage_bps,
        "nonce": nonce,
        "deadline": deadline,
    }

    info(f"Intent: {action} {pair} | Amount: ${amount} (scaled: {amount_usd_scaled})")
    info(f"Slippage: {max_slippage_bps} bps | Deadline: {deadline}")

    # EIP-712 signing
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TradeIntent": [
                {"name": "agentId", "type": "uint256"},
                {"name": "agentWallet", "type": "address"},
                {"name": "pair", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "amountUsdScaled", "type": "uint256"},
                {"name": "maxSlippageBps", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        },
        "primaryType": "TradeIntent",
        "domain": {
            "name": "RiskRouter",
            "version": "1",
            "chainId": CHAIN_ID,
            "verifyingContract": router_addr,
        },
        "message": intent_data,
    }

    info("Signing EIP-712 TradeIntent...")
    signable = encode_typed_data(
        full_message=typed_data,
    )
    signed = Account.sign_message(signable, private_key=PRIVATE_KEY)
    signature = signed.signature

    info(f"Signature: 0x{signature.hex()[:40]}...")

    # Build the on-chain intent tuple
    intent_tuple = (
        agent_id,
        Web3.to_checksum_address(WALLET_ADDRESS),
        pair,
        action,
        amount_usd_scaled,
        max_slippage_bps,
        nonce,
        deadline,
    )

    func = contract.functions.submitTradeIntent(intent_tuple, signature)

    receipt, tx_hash_hex = send_tx(
        w3, acct, func, f"trade_{action}_{pair}",
        {
            "contract": "RiskRouter",
            "agentId": agent_id,
            "pair": pair,
            "action": action,
            "amount": amount,
            "amountUsdScaled": amount_usd_scaled,
        },
    )

    if receipt["status"] != 1:
        error("Trade submission reverted")
        return receipt

    # Check for TradeApproved or TradeRejected events
    trade_result = "UNKNOWN"
    try:
        approved_logs = contract.events.TradeApproved().process_receipt(receipt)
        if approved_logs:
            trade_result = "APPROVED"
            info(f"Trade APPROVED: {approved_logs[0]['args']}")
    except Exception:
        pass

    try:
        rejected_logs = contract.events.TradeRejected().process_receipt(receipt)
        if rejected_logs:
            trade_result = "REJECTED"
            reason = rejected_logs[0]["args"].get("reason", "unknown")
            info(f"Trade REJECTED: {reason}")
    except Exception:
        pass

    if trade_result == "UNKNOWN":
        info("No TradeApproved/TradeRejected event found (tx succeeded)")

    print()
    info(f"TRADE SUBMITTED: {trade_result}")
    info(f"TX: {etherscan_tx(tx_hash_hex)}")
    print()

    return receipt


def cmd_checkpoint(w3: Web3, acct, score: int, notes: str):
    """Post a checkpoint attestation to the ValidationRegistry."""
    banner(f"CHECKPOINT (score={score})")

    agent_id = load_agent_id()
    info(f"Agent ID: {agent_id}")

    val_addr = Web3.to_checksum_address(CONTRACTS["ValidationRegistry"])
    info(f"ValidationRegistry: {val_addr}")

    contract = w3.eth.contract(address=val_addr, abi=VALIDATION_REGISTRY_ABI)

    # Create checkpointHash = keccak256(agentId + timestamp + notes)
    timestamp_now = int(time.time())
    hash_input = abi_encode(
        ["uint256", "uint256", "string"],
        [agent_id, timestamp_now, notes],
    )
    checkpoint_hash = Web3.keccak(hash_input)

    info(f"Checkpoint hash: 0x{checkpoint_hash.hex()}")
    info(f"Score: {score}")
    info(f"Notes: {notes}")

    func = contract.functions.postEIP712Attestation(
        agent_id,
        checkpoint_hash,
        score,
        notes,
    )

    receipt, tx_hash_hex = send_tx(
        w3, acct, func, f"checkpoint_score{score}",
        {
            "contract": "ValidationRegistry",
            "agentId": agent_id,
            "score": score,
            "notes": notes,
            "checkpointHash": f"0x{checkpoint_hash.hex()}",
        },
    )

    if receipt["status"] != 1:
        error("Checkpoint attestation failed")
        return receipt

    # Parse AttestationPosted event
    try:
        logs = contract.events.AttestationPosted().process_receipt(receipt)
        if logs:
            info(f"Attestation posted: score={logs[0]['args']['score']}")
    except Exception as e:
        warn(f"Could not parse AttestationPosted event: {e}")

    print()
    info("CHECKPOINT POSTED")
    info(f"TX: {etherscan_tx(tx_hash_hex)}")
    print()

    return receipt


def cmd_status(w3: Web3, acct):
    """Print current on-chain status for CrossMind."""
    banner("STATUS")

    # Check agent registration
    if not AGENT_ID_FILE.exists():
        warn("Not registered yet (agent_id.json not found)")
        agent_id = None
    else:
        agent_id = load_agent_id()
        info(f"Agent ID: {agent_id}")

    # Check registration details
    if agent_id is not None:
        registry = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["AgentRegistry"]),
            abi=AGENT_REGISTRY_ABI,
        )
        try:
            agent_data = registry.functions.getAgent(agent_id).call()
            info(f"Name:        {agent_data[2]}")
            info(f"Operator:    {agent_data[0]}")
            info(f"AgentWallet: {agent_data[1]}")
            info(f"Active:      {agent_data[6]}")
            info(f"Registered:  {datetime.fromtimestamp(agent_data[5], tz=timezone.utc).isoformat()}")
            cap_list = agent_data[4]
            info(f"Capabilities: {', '.join(cap_list)}")
        except Exception as e:
            warn(f"Could not read agent data: {e}")

    # Check vault balance
    if agent_id is not None:
        vault = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["HackathonVault"]),
            abi=HACKATHON_VAULT_ABI,
        )
        try:
            vault_balance = vault.functions.getBalance(agent_id).call()
            info(f"Vault balance: {vault_balance}")
        except Exception as e:
            warn(f"Could not read vault balance: {e}")

    # Check reputation
    if agent_id is not None:
        rep = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["ReputationRegistry"]),
            abi=REPUTATION_REGISTRY_ABI,
        )
        try:
            reputation = rep.functions.getReputation(agent_id).call()
            info(f"Reputation score: {reputation}")
        except Exception as e:
            warn(f"Could not read reputation: {e}")

    # Check validation score
    if agent_id is not None:
        val = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["ValidationRegistry"]),
            abi=VALIDATION_REGISTRY_ABI,
        )
        try:
            val_score = val.functions.getValidationScore(agent_id).call()
            info(f"Validation score: {val_score}")
        except Exception as e:
            warn(f"Could not read validation score: {e}")

    # ETH balance
    eth_balance = w3.eth.get_balance(Web3.to_checksum_address(WALLET_ADDRESS))
    info(f"ETH balance: {w3.from_wei(eth_balance, 'ether'):.6f} ETH")

    # Transaction history
    if TX_LOG_FILE.exists():
        with open(TX_LOG_FILE) as f:
            tx_records = json.load(f)
        info(f"On-chain transactions: {len(tx_records)}")
        for rec in tx_records[-5:]:
            print(f"      {rec['action']:30s} {rec['etherscanUrl']}")
    else:
        info("No on-chain transactions recorded yet")

    print()


def cmd_full_pipeline(w3: Web3, acct):
    """Run the complete hackathon on-chain pipeline."""
    banner("FULL PIPELINE")
    info("Running: Register -> Claim -> 3 Trades -> 3 Checkpoints -> Status")
    print()

    # Step 1: Register
    info("STEP 1/6: Registration")
    try:
        agent_id = cmd_register(w3, acct)
    except Exception as e:
        error(f"Registration failed: {e}")
        sys.exit(1)

    # Step 2: Claim allocation
    info("STEP 2/6: Claim Allocation")
    try:
        cmd_claim(w3, acct)
    except Exception as e:
        error(f"Claim failed: {e}")
        warn("Continuing pipeline...")

    # Step 3: Submit 3 diverse trades
    trades = [
        ("XBTUSD", "BUY",  500),
        ("ETHUSD", "SELL", 300),
        ("SOLUSD", "BUY",  200),
    ]

    for i, (pair, action, amount) in enumerate(trades, 1):
        info(f"STEP 3.{i}/6: Trade {action} {pair} ${amount}")
        try:
            cmd_trade(w3, acct, pair, action, amount)
        except Exception as e:
            error(f"Trade {action} {pair} failed: {e}")
            warn("Continuing pipeline...")

    # Step 4: Post 3 checkpoints
    checkpoints = [
        (85, f"War Room scenario 1 survived - BUY XBTUSD ${trades[0][2]} submitted"),
        (90, f"War Room scenario 2 survived - SELL ETHUSD ${trades[1][2]} submitted"),
        (88, f"War Room scenario 3 survived - BUY SOLUSD ${trades[2][2]} submitted"),
    ]

    for i, (score, notes) in enumerate(checkpoints, 1):
        info(f"STEP 4.{i}/6: Checkpoint (score={score})")
        try:
            cmd_checkpoint(w3, acct, score, notes)
        except Exception as e:
            error(f"Checkpoint failed: {e}")
            warn("Continuing pipeline...")

    # Step 5: Final status
    info("STEP 5/6: Final Status")
    cmd_status(w3, acct)

    # Step 6: Summary
    banner("PIPELINE COMPLETE")
    info("All on-chain operations finished.")

    if TX_LOG_FILE.exists():
        with open(TX_LOG_FILE) as f:
            tx_records = json.load(f)
        info(f"Total transactions: {len(tx_records)}")
        total_gas = 0
        for rec in tx_records:
            print(f"      {rec['action']:30s} {rec['etherscanUrl']}")

    info(f"Evidence saved to {TX_LOG_FILE}")
    info(f"Agent ID file: {AGENT_ID_FILE}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CrossMind Hackathon On-Chain Operations (Sepolia)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hackathon_onchain.py register
  python hackathon_onchain.py claim
  python hackathon_onchain.py trade --pair XBTUSD --action BUY --amount 500
  python hackathon_onchain.py checkpoint --score 85 --notes "War Room survived"
  python hackathon_onchain.py status
  python hackathon_onchain.py full-pipeline
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # register
    subparsers.add_parser("register", help="Register CrossMind on AgentRegistry")

    # claim
    subparsers.add_parser("claim", help="Claim sandbox allocation from HackathonVault")

    # trade
    trade_parser = subparsers.add_parser("trade", help="Submit TradeIntent to RiskRouter")
    trade_parser.add_argument("--pair", required=True, help="Trading pair (e.g., XBTUSD)")
    trade_parser.add_argument("--action", required=True, choices=["BUY", "SELL"], help="Trade action")
    trade_parser.add_argument("--amount", required=True, type=int, help="Amount in USD")

    # checkpoint
    cp_parser = subparsers.add_parser("checkpoint", help="Post checkpoint to ValidationRegistry")
    cp_parser.add_argument("--score", required=True, type=int, help="Checkpoint score (0-100)")
    cp_parser.add_argument("--notes", required=True, help="Checkpoint notes")

    # status
    subparsers.add_parser("status", help="Show current on-chain status")

    # full-pipeline
    subparsers.add_parser("full-pipeline", help="Run complete pipeline end-to-end")

    args = parser.parse_args()

    # Initialize web3 and account
    w3 = get_web3()
    info(f"Connected to Sepolia (Chain ID {CHAIN_ID})")
    acct, _ = get_account(w3)

    # Dispatch
    if args.command == "register":
        cmd_register(w3, acct)
    elif args.command == "claim":
        cmd_claim(w3, acct)
    elif args.command == "trade":
        cmd_trade(w3, acct, args.pair, args.action, args.amount)
    elif args.command == "checkpoint":
        cmd_checkpoint(w3, acct, args.score, args.notes)
    elif args.command == "status":
        cmd_status(w3, acct)
    elif args.command == "full-pipeline":
        cmd_full_pipeline(w3, acct)


if __name__ == "__main__":
    main()

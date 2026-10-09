#!/usr/bin/env bash
# =============================================================================
# Automated Setup Script for ZohaibChain1
# Creates and initializes the IoV blockchain network, streams, and assets.
# =============================================================================

set -e

CHAIN_NAME="zohaibchain1"

echo "==========================================================================="
echo "  ZOHAIBCHAIN1: AUTOMATED BLOCKCHAIN INITIALIZATION SCRIPT"
echo "==========================================================================="

# 1. Check if multichain is installed
if ! command -v multichaind &> /dev/null; then
    echo "[-] MultiChain is not found on your PATH."
    echo "[*] To install MultiChain 2.3.3 on Ubuntu/Debian:"
    echo "    wget https://www.multichain.com/download/multichain-2.3.3.tar.gz"
    echo "    tar -xvzf multichain-2.3.3.tar.gz"
    echo "    sudo mv multichain-2.3.3/multichain* /usr/local/bin/"
    exit 1
fi

echo "[+] MultiChain binaries detected."

# 2. Check if chain already exists
CONFIG_DIR="$HOME/.multichain/$CHAIN_NAME"
if [ ! -d "$CONFIG_DIR" ]; then
    echo "[*] Creating new blockchain: $CHAIN_NAME..."
    multichain-util create "$CHAIN_NAME"
    # Set fast block time for IoV (3 seconds)
    sed -i 's/target-block-time = 15/target-block-time = 3/' "$CONFIG_DIR/params.dat"
    echo "[+] Set target-block-time = 3 seconds."
else
    echo "[+] Blockchain $CHAIN_NAME directory already exists."
fi

# 3. Start daemon if not running
if ! multichain-cli "$CHAIN_NAME" getinfo &> /dev/null; then
    echo "[*] Starting $CHAIN_NAME daemon in background..."
    multichaind "$CHAIN_NAME" -daemon
    sleep 3
else
    echo "[+] Daemon $CHAIN_NAME is already running."
fi

# 4. Get Primary Admin Address
ADMIN_ADDR=$(multichain-cli "$CHAIN_NAME" getaddresses | grep -o '"1[^"]*"' | head -n 1 | tr -d '"')
echo "[+] Detected Admin Node Address: $ADMIN_ADDR"

# 5. Create paper registers (streams) if not already existing
echo "[*] Initializing paper data streams..."
for s in session_register ptr_stream ssr_stream vehicle_register revocation_list; do
    if ! multichain-cli "$CHAIN_NAME" liststreams | grep -q "\"$s\""; then
        echo "  - Creating stream: $s"
        multichain-cli "$CHAIN_NAME" create stream "$s" false > /dev/null
    else
        echo "  - Stream '$s' already active."
    fi
done

# 6. Issue native incentive asset if not already issued
if ! multichain-cli "$CHAIN_NAME" listassets | grep -q "\"iov_credit\""; then
    echo "[*] Minting native IoV reward token: iov_credit (100,000 supply)..."
    multichain-cli "$CHAIN_NAME" issue "$ADMIN_ADDR" iov_credit 100000 1 > /dev/null
    echo "[+] Asset 'iov_credit' issued successfully."
else
    echo "[+] Asset 'iov_credit' is already active."
fi

echo ""
echo "==========================================================================="
echo "  [✔] ZOHAIBCHAIN1 READY FOR IOV SIMULATION & BENCHMARKING!"
echo "==========================================================================="
echo "You can now run:"
echo "  python3 -m unittest discover tests"
echo "  python3 -m src.simulate_iov"
echo "  python3 -m src.benchmark"
echo "==========================================================================="

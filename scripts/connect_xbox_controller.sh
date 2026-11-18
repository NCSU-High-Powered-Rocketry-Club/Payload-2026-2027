
#!/bin/bash

# Connect an Xbox Bluetooth controller to a Raspberry Pi.
# Run with: sudo bash connect_xbox_controller.sh

set -e

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo bash $0"
    exit 1
fi

# Install Bluetooth tools if needed
if ! command -v bluetoothctl &> /dev/null; then
    echo "Installing Bluetooth tools..."
    apt update -qq
    apt install -y -qq bluez
fi

# Start Bluetooth service
systemctl enable bluetooth >/dev/null 2>&1
systemctl start bluetooth

# Initialize Bluetooth
bluetoothctl power on >/dev/null 2>&1
bluetoothctl agent on >/dev/null 2>&1
bluetoothctl default-agent >/dev/null 2>&1

echo "Put Xbox controller into pairing mode."
read -p "Press ENTER when ready... "

# Scan for devices
echo "Scanning..."
bluetoothctl --timeout 15 scan on > /tmp/bluetooth_scan.log 2>&1 || true

# Search for lines containing BOTH Xbox and controller
MAC=$(grep -i 'Xbox' /tmp/bluetooth_scan.log \
    | grep -i 'controller' \
    | grep -oE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' \
    | head -n 1 || true)

# Ask for MAC if automatic detection fails
if [[ -z "$MAC" ]]; then
    echo "Xbox controller not automatically detected."
    read -p "Enter controller MAC address: " MAC
fi

# Validate MAC address
if [[ ! "$MAC" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
    echo "Invalid MAC address."
    exit 1
fi

# Pair, trust, and connect
echo "Connecting controller..."

bluetoothctl pair "$MAC" >/dev/null 2>&1
bluetoothctl trust "$MAC" >/dev/null 2>&1
bluetoothctl connect "$MAC" >/dev/null 2>&1
bluetoothctl scan off >/dev/null 2>&1 || true

echo "Xbox controller connected successfully."


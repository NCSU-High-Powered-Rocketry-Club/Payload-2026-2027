
#!/bin/bash

# Automatically detect, pair, trust, and connect
# an Xbox Bluetooth controller to a Raspberry Pi.
#
# Run with:
# sudo bash connect_xbox_controller.sh

set -euo pipefail

# ----------------------------------------
# 1. Check permissions
# ----------------------------------------

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run with sudo."
    exit 1
fi

# ----------------------------------------
# 2. Install Bluetooth tools if necessary
# ----------------------------------------

if ! command -v bluetoothctl &>/dev/null; then
    echo "Installing Bluetooth tools..."
    apt update
    apt install -y bluez
fi

# ----------------------------------------
# 3. Start Bluetooth service
# ----------------------------------------

echo ""
echo "[1/7] Starting Bluetooth service..."

systemctl enable bluetooth
systemctl start bluetooth

# ----------------------------------------
# 4. Initialize Bluetooth adapter
# ----------------------------------------

echo ""
echo "[2/7] Initializing Bluetooth adapter..."

bluetoothctl power on >/dev/null

# ----------------------------------------
# 5. Scan for Xbox controller
# ----------------------------------------

echo ""
echo "[3/7] Searching for Xbox controller..."
echo "Waiting for controller advertising..."

MAC=""

for attempt in {1..6}; do

    echo "Bluetooth scan $attempt/6..."

    # Scan for 15 seconds
    bluetoothctl --timeout 15 scan on >/dev/null 2>&1 || true

    # Find Xbox controller in discovered devices
    MAC=$(
        bluetoothctl devices |
        grep -iE 'Xbox.*(Controller|Wireless)|Controller.*Xbox' |
        awk 'NR==1 {print $2}'
    )

    if [[ -n "$MAC" ]]; then
        break
    fi

done

# ----------------------------------------
# 6. Verify controller was discovered
# ----------------------------------------

if [[ -z "$MAC" ]]; then
    echo ""
    echo "ERROR: No Xbox controller detected."
    echo ""
    echo "Make sure:"
    echo "- The controller is powered on."
    echo "- The pairing button is held."
    echo "- The Xbox button is flashing rapidly."
    exit 1
fi

echo ""
echo "Xbox controller detected!"
echo "MAC address: $MAC"

# ----------------------------------------
# 7. Pair, trust, and connect
# ----------------------------------------

echo ""
echo "[4/7] Registering Bluetooth pairing agent..."

LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

# Keep one bluetoothctl session open so that
# the pairing agent remains registered.

{
    echo "agent NoInputNoOutput"
    sleep 1

    echo "default-agent"
    sleep 1

    echo "pair $MAC"
    sleep 12

    echo "trust $MAC"
    sleep 2

    echo "connect $MAC"
    sleep 8

    echo "info $MAC"
    sleep 2

    echo "quit"

} | bluetoothctl 2>&1 | tee "$LOG"

# ----------------------------------------
# 8. Verify Bluetooth connection
# ----------------------------------------

echo ""
echo "[5/7] Verifying Bluetooth connection..."

INFO=$(bluetoothctl info "$MAC")

if ! grep -q "Connected: yes" <<< "$INFO"; then
    echo ""
    echo "ERROR: Controller was discovered but connection failed."
    echo "$INFO"
    exit 1
fi

if ! grep -q "Paired: yes" <<< "$INFO"; then
    echo "ERROR: Controller is not paired."
    exit 1
fi

if ! grep -q "Trusted: yes" <<< "$INFO"; then
    echo "ERROR: Controller is not trusted."
    exit 1
fi

echo ""
echo "Bluetooth connection successful!"

# ----------------------------------------
# 9. Verify Linux input device
# ----------------------------------------

echo ""
echo "[6/7] Checking Linux input devices..."

sleep 2

if ls /dev/input/js* &>/dev/null; then

    echo "Joystick device detected:"
    ls /dev/input/js*

else

    echo "WARNING: No joystick device found yet."
    echo "Bluetooth is connected, but Linux has not"
    echo "created a joystick interface."

fi

# ----------------------------------------
# 10. Final status
# ----------------------------------------

echo ""
echo "[7/7] Final controller status:"
echo ""

bluetoothctl info "$MAC"

echo ""
echo "========================================"
echo " Xbox controller connection process done"
echo "========================================"

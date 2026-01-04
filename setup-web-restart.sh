#!/bin/bash
#
# Configure sudo to allow web_control.py to restart the streaming service
# without requiring a password
#

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root: sudo ./setup-web-restart.sh"
    exit 1
fi

echo "Configuring sudo for web_control restart capability..."

# Create sudoers file for turntable restart
cat > /etc/sudoers.d/turntable-web <<'EOF'
# Allow any user to restart turntable-stream service without password
# This enables the web control interface to restart the service
ALL ALL=(ALL) NOPASSWD: /bin/systemctl restart turntable-stream
EOF

# Set proper permissions on sudoers file
chmod 0440 /etc/sudoers.d/turntable-web

# Verify syntax
if visudo -c -f /etc/sudoers.d/turntable-web; then
    echo "✅ Sudo configuration successful!"
    echo ""
    echo "The web interface can now restart the streaming server."
    echo "Visit http://YOUR_PI_IP:8080/settings to try it!"
else
    echo "❌ Error in sudoers configuration, removing file..."
    rm -f /etc/sudoers.d/turntable-web
    exit 1
fi


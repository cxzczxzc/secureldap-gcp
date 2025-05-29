#!/bin/bash
# This script starts the SSSD service and restarts SSH daemon to apply changes.
# It is intended to be run with sudo permissions.

# 1. Start SSSD and restart SSH daemon
function start_sssd() {
    echo "Enabling and restarting SSSD..."
    sudo systemctl daemon-reload  # Good practice after changing system configs
    sudo systemctl enable sssd    # Enable SSSD to start on boot
    sudo systemctl restart sssd   # Restart SSSD to apply its new configuration

    echo "Waiting for SSSD to initialize (10-15 seconds)..."
    sleep 15 # Give SSSD time to connect to LDAP and cache initial info

    echo "Restarting SSH daemon..."
    sudo systemctl restart sshd   # Restart SSH daemon to apply PAM and any sshd_config changes
                                # (Some systems might use ssh.service instead of sshd.service)
}


# 2. Health check for SSSD service
function check_sssd_health() {
    echo "Checking SSSD service health..."
    echo "Checking SSSD status..."
    sudo systemctl status sssd --no-pager
    echo "Checking recent SSSD logs (look for successful connection to ldap.google.com or any errors)..."
    sudo journalctl -u sssd -n 50 --no-pager
}
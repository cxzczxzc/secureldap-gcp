#!/bin/bash
# This file is for configuring Name Service Switch (NSS) on a GCE instance.
# It is intended to be run with sudo permissions.
# This file tells the Linux operating system which services to use for looking up 
# different types of system information (like user accounts, group information, hostnames, etc.). 
# It needs to be configured to use sss (SSSD) for users and groups.


# 1. Backup existing NSS configuration files
function backup_nss_files() {
    local source_file="/etc/nsswitch.conf"
    # Define the backup filename, incorporating a timestamp for uniqueness
    # Using %F for YYYY-MM-DD and %T for HH:MM:SS 
    local backup_file="${source_file}.bak_$(date +%F_%H-%M-%S)" # e.g., /etc/nsswitch.conf.bak_2025-05-28_18-41-00

    echo "INFO: Attempting to back up '${source_file}' to '${backup_file}'..."

    # Execute the backup command with sudo
    # The 'if' statement directly checks the exit status of 'sudo cp'
    if sudo cp "${source_file}" "${backup_file}"; then
        # Command was successful (exit status 0)
        echo "INFO: Successfully backed up '${source_file}' to '${backup_file}'."
        return 0 # Indicate success
    else
        # Command failed (non-zero exit status)
        local exit_status=$? # Capture the exit status
        echo "ERROR: Failed to back up '${source_file}'." >&2
        echo "ERROR: The 'sudo cp' command exited with status ${exit_status}." >&2
        echo "ERROR: Please check permissions, if the source file exists, or if sudo privileges are sufficient." >&2
        return 1 # Indicate failure
    fi
}
# 2. Function to update /etc/nsswitch.conf for passwd, group, and shadow entries
function update_nss_config() {
    local nsswitch_file="/etc/nsswitch.conf"
    echo "INFO: Updating ${nsswitch_file} for passwd, group, and shadow services..."
    if sudo sed -i 's/^passwd:.*/passwd: files systemd sss/' "${nsswitch_file}"; then
        echo "INFO: passwd line updated in ${nsswitch_file}."
    else
        echo "ERROR: Failed to update passwd line in ${nsswitch_file}." >&2
        return 1 # Indicate failure
    fi
    # Modify group line
    # Desired: group: files systemd sss
    if sudo sed -i 's/^group:.*/group: files systemd sss/' "${nsswitch_file}"; then
        echo "INFO: group line updated in ${nsswitch_file}."
    else
        echo "ERROR: Failed to update group line in ${nsswitch_file}." >&2
        return 1 # Indicate failure
    fi
    # Modify shadow line
    # Desired: shadow: files sss
    if sudo sed -i 's/^shadow:.*/shadow: files sss/' "${nsswitch_file}"; then
        echo "INFO: shadow line updated in ${nsswitch_file}."
    else
        echo "ERROR: Failed to update shadow line in ${nsswitch_file}." >&2
        return 1 # Indicate failure
    fi
    echo "INFO: ${nsswitch_file} update process complete."
    return 0 # Indicate success
}
backup_nss_files
update_nss_config


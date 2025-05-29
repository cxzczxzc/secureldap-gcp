#!/bin/bash

# ==============================================================================
# Function: secure_ssh_config
# Description: Hardens the sshd_config file with recommended security settings.
#
# This function will:
# 1. Check for root privileges.
# 2. Create a timestamped backup of the original /etc/ssh/sshd_config file.
# 3. Update or add the specified security parameters.
#
# Usage:
#   source update_ssh.sh
#   sudo bash -c 'secure_ssh_config'
# ==============================================================================
function secure_ssh_config() {
    local sshd_config_file="/etc/ssh/sshd_config"

    # --- 1. Check for root privileges ---
    if [[ "${EUID}" -ne 0 ]]; then
        echo "ERROR: This script must be run as root. Please use sudo."
        return 1
    fi

    # --- 2. Create a backup ---
    local backup_file="/etc/ssh/sshd_config.bak.$(date +%Y%m%d_%H%M%S)"
    echo "INFO: Creating backup of current configuration at ${backup_file}"
    cp "${sshd_config_file}" "${backup_file}"
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Failed to create backup file. Aborting."
        return 1
    fi

    # --- 3. Define settings to apply ---
    # Using an associative array to hold key-value pairs
    declare -A settings
    settings["UsePAM"]="yes"
    settings["PubkeyAuthentication"]="yes"
    settings["PasswordAuthentication"]="no"
    settings["ChallengeResponseAuthentication"]="no"
    settings["PermitRootLogin"]="prohibit-password"

    echo "INFO: Applying security settings..."

    # --- 4. Update or add each setting ---
    for key in "${!settings[@]}"; do
        value="${settings[$key]}"
        # Check if the setting exists (commented or not)
        if grep -qE "^\s*#?\s*${key}" "${sshd_config_file}"; then
            # If it exists, use sed to uncomment and set the correct value
            echo " -> Updating '${key}' to '${value}'"
            sed -i "s/^\s*#*\s*${key}.*/${key} ${value}/" "${sshd_config_file}"
        else
            # If it doesn't exist, append it to the end of the file
            echo " -> Adding '${key} ${value}'"
            echo "${key} ${value}" >> "${sshd_config_file}"
        fi
    done

    echo -e "\nSUCCESS: The sshd_config file has been updated."
    echo "--------------------------------------------------------"
    echo "IMPORTANT: To apply the changes, you must validate the configuration and restart the SSH service."
    echo "1. Validate syntax: sudo sshd -t"
    echo "2. Restart service: sudo systemctl restart sshd"
    echo "--------------------------------------------------------"
}

secure_ssh_config

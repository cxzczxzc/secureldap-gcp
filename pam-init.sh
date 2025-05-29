#!/bin/bash
# This script initializes the Pluggable Authentication Modules for use with SSSD.
# It is intended to be run with sudo permissions.

OS = cat /etc/os-release
function configure_pam_ubuntu() {
    echo "Configuring PAM for SSSD on $OS..."
    sudo pam-auth-update --enable sss
}

function configure_pam_rhel() {
    echo "Configuring PAM for SSSD on $OS..."
    sudo authselect select sssd with-mkhomedir --force
}

configure_pam_ubuntu
# configure_pam_rhel
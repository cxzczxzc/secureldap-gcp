#!/bin/bash
# This script intalls and configures SSSD for POSIX attribute updates on a GCE instance.
# It is intended to be run with sudo permissions.
OS=cat /etc/os-release
# Function to install SSSD on debian/ubuntu systems
function install_sssd_debian_ubuntu() {
    echo "Installing SSSD on $OS..."
    sudo apt update
    sudo apt install -y sssd sssd-ldap sssd-tools ldap-utils libnss-sss libpam-sss
    sudo apt install libsasl2-modules libsasl2-modules-ldap
}
# Function to install SSSD on RHEL/CentOS systems
function install_sssd_rhel_centos() {
    echo "Installing SSSD on $OS..."
    sudo dnf install -y sssd sssd-ldap sssd-tools openldap-clients authselect-compat
}
# add logic for updating /etc/sssd/sssd.conf from existing template
function configure_sssd() {
    echo "Configuring SSSD..."
    # Create the SSSD configuration file
    sudo tee /etc/sssd/sssd.conf > /dev/null 
}
# configure sssd permissions
function set_sssd_permissions() {
    echo "Setting permissions for SSSD configuration file..."
    sudo chmod 600 /etc/sssd/sssd.conf
    sudo chown root:root /etc/sssd/sssd.conf
}

install_sssd_debian_ubuntu
configure_sssd
set_sssd_permissions
#install_sssd_rhel_centos
#!/bin/bash
# Secure LDAP Installation Script
# This script is intended to be run on a Google Cloud VM instance with sudo permissions
# The service account needs to have the "Secret Manager Secret Accessor" role
# This script does the following:
# 1. Downloads certificate and key file for Secure LDAP from secret manager
# 2. Creates a directory for the certificate and key files /etc/secureldap/certs
# 3. Moves the downloaded cert files to the created directory
# 4. Sets the correct permissions for the certificate and key files


# 1. Downloads certificate and key file for Secure LDAP from secret manager
function download_sldap_cert() {
    echo "Downloading Secure LDAP certificate and key from Google Cloud Secret Manager..."
    gcloud secrets versions access latest --secret="sldap_cert" --project="sldap-suplex" > ./sldap.crt
    gcloud secrets versions access latest --secret="sldap_cert_key" --project="sldap-suplex" > ./sldap-cert-key.key
}


# 2. Creates a directory for the certificate and key files /etc/secureldap/certs
function create_cert_directory() {
    echo "Creating directory for Secure LDAP certificates..."
    if [ ! -d "/etc/secureldap/certs" ]; then
        sudo mkdir -p /etc/secureldap/certs
    fi
}

function move_cert_files() {
    echo "Moving Secure LDAP certificate and key files to /etc/secureldap/certs..."
    # Check if the files exist before moving
    if [ -f "./sldap.crt" ] && [ -f "./sldap-cert-key.key" ]; then
        sudo mv ./sldap.crt /etc/secureldap/certs
        sudo mv ./sldap-cert-key.key /etc/secureldap/certs
    else
        echo "Certificate or key file not found. Please check the download step."
        exit 1
    fi
}

function set_sldap_cert_permissions() {
    echo "Setting permissions for Secure LDAP certificate and key files..."
    # Set the correct permissions for the certificate and key files
    sudo chmod 0644 /etc/secureldap/certs/sldap.crt
    sudo chmod 0600 /etc/secureldap/certs/sldap-cert-key.key # rw- for owner, no permissions for group and others
}

download_sldap_cert
create_cert_directory
move_cert_files
set_sldap_cert_permissions
echo "Secure LDAP certificate and key files have been successfully set up."
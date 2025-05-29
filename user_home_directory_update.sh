#!/bin/bash
# This script moves the contents of the old OS Login home directory to the new LDAP home directory for a specific user.
# It is intended to be run with sudo permissions.
# OS Login might have assigned the home directory in a different pattern, so we need to adjust accordingly
# to the new LDAP home directory structure, based on the POSIX attributes set in LDAP.


USER="demouser1" # Replace with the actual usernamme, aligning with posix attributes set in LDAP (homeDirectory, uidNumber, gidNumber, loginshell, etc.)
OLD_OSLOGIN_HOME_DIRECTORY="/home/demouser1_saadx_altostrat_com" # Adjust if OSLogin used a different pattern
NEW_LDAP_HOME_DIRECTORY="/home/${USER}"
USER_UID="1001" # Replace with the actual UID for demouser1
USER_GID="2001" # Replace with the actual GID for demouser1

if [ -d "${OLD_OSLOGIN_HOME_DIRECTORY}" ]; then
    if [ -d "${NEW_LDAP_HOME_DIRECTORY}" ]; then # New home should have been created by pam_mkhomedir
        echo "Moving contents from ${OLD_OSLOGIN_HOME_DIRECTORY} to ${NEW_LDAP_HOME_DIRECTORY} for demouser1..."
        # Use rsync to copy contents. Add --remove-source-files to rsync to truly move.
        sudo rsync -av "${OLD_OSLOGIN_HOME_DIRECTORY}/" "${NEW_LDAP_HOME_DIRECTORY}/"
        # Ensure ownership is correct on all contents after rsync (UID 1001, GID 2001 for demouser1)
        sudo chown -R "${USER_UID}:${USER_GID}" "${NEW_LDAP_HOME_DIRECTORY}"
        echo "Contents moved/synced. You may want to manually verify and then remove the old directory:"
        echo "sudo rm -rf ${OLD_OSLOGIN_HOME_DIRECTORY}"
    else
        echo "Warning: New LDAP home ${NEW_LDAP_HOME_DIRECTORY} not found, but OS Login home exists."
        echo "Consider renaming: sudo mv ${OLD_OSLOGIN_HOME_DIRECTORY} ${NEW_LDAP_HOME_DIRECTORY}"
        echo "Then ensure ownership: sudo chown -R 1001:2001 ${NEW_LDAP_HOME_DIRECTORY}"
    fi
else
    echo "Old OS Login home directory for demouser1 not found at ${OLD_OSLOGIN_HOME_DIRECTORY}. No file move needed from there."
fi
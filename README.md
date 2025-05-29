# Secure LDAP Setup Steps
This repository provides the necessary scripts and guidance to integrate your systems with Google's Secure LDAP service. This setup is particularly useful when managing user identities in an external Identity Provider (IdP) like Entra ID (formerly Azure AD) and synchronizing them to Google Cloud Identity for services that rely on LDAP for authentication and POSIX attributes.

In this example, user identities originate in **Entra ID** and are synchronized to Google Cloud Identity using the "Entra ID Enterprise App for G Suite" (now Google Workspace). 

Single Sign-On (SSO) is assumed to be enabled with MFA, ensuring a seamless authentication experience, and both user and group information are propagated to Cloud Identity.

## Goal

The primary objective of implementing Secure LDAP in this scenario is to enable centralized user authentication for  **Google Compute Engine VMs**. By leveraging Secure LDAP, users can authenticate to these VMs using their existing corporate credentials. Furthermore, this setup allows for the utilization of `posixAttributes` (such as `uid` - user ID, `gid` - group ID, `homeDirectory`, and `loginShell`) stored in Cloud Identity. These attributes are crucial for:

- **Consistent File Permissions:** Maintaining consistent access control and ownership of files and directories on the VM's operating system, regardless of which VM a user logs into.
- **Application Compatibility:** Ensuring that applications requiring POSIX-compliant user information function correctly.
- **Centralized User Management:** Managing user access and attributes from a central directory rather than on each individual VM.

## Prerequisites

Before you begin the implementation, ensure the following prerequisites are met within your Google Admin and Google Cloud Platform (GCP) environments:

### Google Admin Console (admin.google.com)
#### 1. Cloud Identity Premium:**
- **Why:** Secure LDAP is a feature of Cloud Identity Premium. Ensure your organization has the appropriate subscription. This edition provides the necessary features for integrating external LDAP clients.

#### 2. Organizational Unit (OU) for Secure LDAP Users:
- **Why:** Create a dedicated OU in Google Cloud Identity (e.g., SecureLDAPEnabledUsers). This allows you to selectively enable Secure LDAP for a specific subset of users and groups, adhering to the principle of least privilege and simplifying management.

- **Action:** Define and create this OU if it doesn't already exist.

#### 3.Users and Groups Assignment:

- **Why:** Only users and groups placed within the OU for which Secure LDAP is enabled will be accessible via the Secure LDAP service.

- **Action:** Add the relevant users and groups (that require LDAP access to GCE VMs) to the designated OU.

#### 4. Secure LDAP Service Enabled:

- **Why:** The Secure LDAP service must be explicitly turned on for the specific OU containing the users and groups.

- **Action:** Navigate to the Secure LDAP settings in the Google Admin console and enable it for the OU created in the previous step.

#### 5. Google Admin SDK Enabled:

- **Why:** The Admin SDK is required by the Python scripts (app.py, get_info.py) in this repository to programmatically interact with Google Cloud Identity, specifically for updating and retrieving user posixAttributes.

- **Action:** Enable the "Admin SDK" API in any of your GCP projects via the GCP Console.

#### 6. OAuth 2.0 Account Credentials for Admin SDK:

- **Why:** To allow the scripts to authenticate and authorize against the Admin SDK, you need oauth account credentials. 
These credentials go through the OAuth2.0 login flow, where the user running the script will be able to login.
The user running the script must have `User Management Administrator`, which can be assigned from the Google Admin Console, under Accounts > Admin roles.

- **Security Note:** Treat this `credentials.json` file as highly sensitive. Do not commit it to public repositories. Use appropriate methods like .gitignore and secure secret management practices.

## Implementation Steps

Follow these steps carefully to configure Secure LDAP client access on your GCE VMs.

### 1.Update Users' `posixAttributes`

This initial step involves setting essential POSIX attributes (uid, gid, homeDirectory, loginShell) for each user in Cloud Identity who will be using Secure LDAP to access GCE VMs. These attributes define the user's identity within a Linux/UNIX environment.
* `uid`: A unique numerical user identifier.
* `gid`: A unique numerical group identifier for the user's primary group.
* `homeDirectory`: The user's default home directory
* `loginShell`: The user's default login shell.

The `update_user_posix_attributes.py` script automates this process by using the Google Admin SDK to update these attributes for users.

Execute the script:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python update_user_posix_attributes.py
```
**Note**: Note: Ensure `credentials.json` is correctly configured before running.

### 2. Verify `posixAttributes` Update

After running `update_user_posix_attributes.py`, confirm that the posixAttributes have been successfully updated in Cloud Identity for the intended users. The `verify_user_posix_attributes.py` script can be used for this verification. It queries Cloud Identity via the Admin SDK and displays the user information, including their POSIX attributes. Check the JSON output to verify the `posixAttributes` section for the users you updated in step 1.
```bash
python verify_user_posix_attributes.py
```

### 3. Download Secure LDAP Client Certificate and Key

From the Google Admin console (under the Secure LDAP service settings for your OU), download the generated LDAP client certificate and its corresponding private key. These files are essential for establishing a secure, encrypted (TLS/SSL) connection between your GCE VMs (LDAP clients) and the Google Secure LDAP service.

- **Action:**
Navigate to Secure LDAP settings in Google Admin console.

Generate and/or download the certificate and key. You'll typically get a `.crt` (certificate) and a `.key` (private key) file.

Secure Storage: Upload these downloaded certificate and key files to Google Cloud Secret Manager in your GCP project. Secret Manager provides a secure and auditable way to store and manage these sensitive files.

Create two secrets: one for the certificate (e.g., `secureldap-cert`) and one for the key (e.g., `secureldap-key`)


#### 4. Grant GCE VM Service Account IAM Permissions

The GCE VMs need permission to access the certificate and key files stored in Secret Manager. This is achieved by granting the VM's service account an appropriate IAM role.

- **Action:**

Identify the service account used by your GCE VMs.

In the GCP IAM console, grant this service account the `roles/secretmanager.secretAccessor` role.

**Principle of Least Privilege:** For enhanced security, instead of granting project-wide access, you can grant this role specifically on the individual certificate and key secrets created in Secret Manager.

### 5. Initialize Secure LDAP Certificates on GCE VM

This step involves transferring the Secure LDAP certificate and key from Secret Manager to the GCE VM and placing them in the expected directory with appropriate permissions. This is performed by SSHing into the GCE VM as a user with sudo or root privileges.

- **Action:**

1. SSH into the GCE VM.

2. Ensure the `sldap-init.sh` script from this repository is present on the VM.

3. Make the script executable: `chmod +x sldap-init.sh`

4. Run the script:
```bash
sudo ./sldap-init.sh
```

- **What `sldap-init.sh` does:**
It  uses gcloud  to fetch the certificate and key from Secret Manager.

Places the certificate and key into `/etc/secureldap/certs/`.

Sets strict file permissions:

`0644` (read/write for owner, read-only for group and others) for the certificate file.

`0600` (read/write for owner, no access for group or others) for the private key file, which is critical for security.

- **Note:** You will need to customize `sldap-init.sh` with your specific Secret Manager secret names and GCP project ID 


### 6. Install and Configure SSSD, NSS, and PAM

To integrate the Linux system on the GCE VM with the Secure LDAP service for authentication and identity lookups, you need to install and configure several components:
1.  **SSSD (System Security Services Daemon):** A daemon that manages access to remote identity and authentication resources, including LDAP. It provides caching for offline logins and improved performance.
2. **NSS (Name Service Switch):** A facility in Unix-like operating systems that provides a pluggable way for the system to look up user, group, host, and other information from various sources (e.g., local files, LDAP).
3. **PAM (Pluggable Authentication Modules):** A framework that allows administrators to configure authentication methods for applications and services without modifying the applications themselves.

The `sssd-init.sh` script automates the installation of these packages and sets up initial permissions for SSSD configuration files.

- **Action:**

Ensure `sssd-init.sh` is on the VM and executable.

Run the script:
```bash
sudo ./sssd-init.sh
```
### 7. Critical SSSD Configuration `/etc/sssd/sssd.conf`

#### IMPORTANT: This is a critical configuration step. The SSSD configuration file, `/etc/sssd/sssd.conf`, dictates how SSSD connects to and interacts with the Google Secure LDAP service. Edit this file manually.

An example `sssd.conf` file can be found in this repo.

**Security Note:** Ensure the permissions on `/etc/sssd/sssd.conf` are restrictive (e.g., 0600), readable only by root, as it may contain sensitive information or pointers to it. The `sssd-init.sh script` set this but its good to verify.

### 8. Configure Name Service Switch NSS - `/etc/nsswitch.conf`

The NSS configuration file tells the system where to look up user, group, and other database information. You need to instruct it to use SSSD for these lookups. The `nss-init.sh` script handles this.

- **Action:**

Ensure `nss-init.sh` is on the VM and executable.

Run the script:

```bash
sudo ./nss-init.sh
```

- **What `nss-init.sh` does:**

1. It creates a backup of the existing /etc/nsswitch.conf.

2. Modifies entries like `passwd`, `group`, and `shadow` to include `sss` (e.g., passwd: files sss). This tells the system to consult SSSD after local files.

### 9. Update SSHD Configuration `/etc/ssh/sshd_config`

The SSH daemon (SSHD) configuration needs to be updated to allow authentication via PAM, which in turn will use SSSD to authenticate users against Secure LDAP. The sshd-init.sh script is designed to make these modifications.

- **Action:**

Ensure `sshd-init.sh` is on the VM and executable.

Run the script:
```bash
sudo ./sshd-init.sh
```
- **What `sshd-init.sh` does**

1. Creates a backup of `/etc/ssh/sshd_config`.

2. Modifies settings like `ChallengeResponseAuthentication`, `PubkeyAuthentication`,`PasswordAuthentication`, and `UsePAM` to enable LDAP-based logins through PAM.

### 10. Restart Services and Perform Health Checks

After all configuration changes, the SSSD and SSHD services must be restarted for the new settings to take effect. The `sssd-run.sh` script handles these restarts and may include some basic health checks.

- **Action:**
1.  Ensure `sssd-run.sh` is on the VM and executable.
2.  Run the script:
```bash
sudo ./sssd-run.sh
```

- **What `sssd-run.sh` does:**
1. Restarts the `sssd` service (e.g., `sudo systemctl restart sssd`).
2. Restarts the `sshd` service (e.g., `sudo systemctl restart sshd` or `sshd`).
3. May check the status of these services and look for errors in relevant log files (e.g., `/var/log/sssd/sssd.log`, `/var/log/secure` or `journalctl`).

- **Troubleshooting:** If this step reports errors, carefully review the logs for SSSD and SSHD to diagnose the issue. Common problems relate to incorrect `sssd.conf` parameters, certificate issues, or network connectivity to `ldap.google.com:636`.

### 11. Verify User Information

The final step is to verify that the system can now retrieve user information from Google Secure LDAP via SSSD. The `getent` command is a standard utility for querying NSS databases.

- **Action:**
From the GCE VM, run:
```bash
getent passwd demouser1
```
(Replace `demouser1` with an actual username of a user who is in the Secure LDAP OU and has `posixAttributes` set).

- **Expected Outcome:**
    If Secure LDAP is configured correctly, this command should return the user's entry, including their UID, GID, home directory, and shell, as retrieved from Secure LDAP. For example:
    `demouser1:x:10001:10001:Demo User:/home/demouser1:/bin/bash`
-  **If it fails:**
1. If the user is not found, or if the command hangs, re-check SSSD logs and configuration.
2. Ensure the user exists in the correct OU with Secure LDAP enabled and `posixAttributes` set.
3. Verify network connectivity to `ldap.google.com` on port `636`.


This completes the Secure LDAP client configuration on the GCE VM. Users should now be able to SSH into the VM using their Google Cloud Identity credentials.

## Critical Watchpoints

### 1. **Users' Home Directory:**The users' home directory might have been configured differently than what is set in the posix attributes. If so, run the `update_user_home_directory.sh` script to update this for maintaining the same access as users had with OS Login.

### 2. **GID/UID collision:** If GIDs/UIDs configured locally on the OS collide with what's configured on Secure LDAP, it can lead to bad access, or lock the user out of the operating system. This happens because NSS is configured to first examine the local os files, such as `etc/passwd` or `etc/groups` before pulling this information from Secure LDAP. 
   
To avoid running into this scenario, UID/GID mapping has to be carefully planned before starting the migration.

### 3. **Groups POSIX Attributes Not Editable (GID):**  [POSIX groups in Cloud Identity](https://cloud.google.com/identity/docs/groups) are scheduled to be deprecated at the same time as OS Login based on POSIX groups. It means that we cannot directly update the `posixAttributes` for a group, the same way we can for a user. 

This leaves us with the following alternatives:

#### Option A: Client-Side GID Definition
- **Mechanism:** Assign group numeric IDs (GIDs) locally on each client system, while using a central directory for group membership lists.
- **Pros:** Control over numeric GIDs, preserves existing file permissions, predictable GID values.
- **Cons:** Decentralized GID definition requires per-client configuration management, potential for local conflicts.

#### Option B: Server-Side GID Provision
- **Mechanism:** Rely on the central directory service to provide group numeric IDs (GIDs) to clients.
- **Pros:** Centralized GID source, simpler client configuration, reduces configuration drift.
- **Cons:** Numeric GIDs may not match desired/legacy values, requires updating file permissions if GIDs change, GIDs can be system-generated and difficult to read.
import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
CREDENTIALS_JSON_PATH = '/Users/saadx/Documents/PSO/2025/Mayo/OS Login POSIX Groups/posix_attribute_update_app/credentials.json'
API_SERVICE_NAME = 'admin'
API_VERSION = 'directory_v1'

# SCOPES required for the operations
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.group'
]

# Data for updates
USERS_TO_UPDATE_CONFIG = {
    "demouser1@saadx.altostrat.com": {
        "uid": "1001", "gid": "2001", "homeDirectory": "/home/demouser1", "shell": "/bin/bash"
    },
    "adminuser1@saadx.altostrat.com": {
        "uid": "1002", "gid": "2001", "homeDirectory": "/home/adminuser1", "shell": "/bin/bash"
    }
}

GROUPS_TO_UPDATE_CONFIG = {
    "gcp_vm_standard_access@saadx.altostrat.com": "2001",
    "gcp_vm_admin_access@saadx.altostrat.com": "2002"
}

class GoogleAdminAuthenticator:
    """Handles authentication with Google Admin SDK."""
    def __init__(self, credentials_path, scopes):
        self.credentials_path = credentials_path
        self.token_path = os.path.join(os.path.dirname(credentials_path), 'token.json')
        self.legacy_token_path = os.path.join(os.path.dirname(credentials_path), 'token.pickle')
        self.scopes = scopes
        self.service_client = self._get_service()

    def _get_service(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
        elif os.path.exists(self.legacy_token_path):
            with open(self.legacy_token_path, 'rb') as token:
                creds = pickle.load(token)
            if creds and creds.valid:
                with open(self.token_path, 'w') as new_token_file:
                    new_token_file.write(creds.to_json())
                os.remove(self.legacy_token_path)
            else:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Deleting old token and re-authenticating...")
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    print(f"ERROR: Credentials file not found at {self.credentials_path}.")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                try:
                    print("Attempting to launch browser for authentication...")
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during OAuth flow: {e}")
                    return None
            
            with open(self.token_path, 'w') as token_file_to_write:
                token_file_to_write.write(creds.to_json())
            print(f"Token saved to: {self.token_path}")

        try:
            return build(API_SERVICE_NAME, API_VERSION, credentials=creds)
        except HttpError as error:
            print(f'An API error occurred building service: {error.resp.status} - {error._get_reason()}')
            return None
        except Exception as e:
            print(f'An unexpected error occurred building service: {e}')
            return None

    def get_service_client(self):
        return self.service_client


class UserManager:
    """Manages POSIX attributes for Google Cloud Identity users."""
    def __init__(self, service_client):
        self.service = service_client

    def get_info(self, user_email, quiet=False):
        try:
            if not quiet:
                print(f"Fetching current data for user: {user_email}")
            user = self.service.users().get(userKey=user_email, projection='full').execute()
            return user
        except HttpError as error:
            if not quiet:
                print(f'API error fetching user {user_email}: {error.resp.status} - {error._get_reason()}')
            return None

    def update_posix_attributes(self, user_email, posix_config):
        current_user_data = self.get_info(user_email, quiet=True)
        if not current_user_data:
            print(f"Skipping update for {user_email}: Could not fetch current data.")
            return False

        email_prefix = user_email.split('@')[0]
        gecos = current_user_data.get("name", {}).get("fullName", email_prefix)

        new_posix_account_entry = {
            "username": email_prefix,
            "uid": posix_config["uid"],
            "gid": posix_config["gid"],
            "homeDirectory": posix_config["homeDirectory"],
            "shell": posix_config["shell"],
            "gecos": gecos,
            "operatingSystemType": "unspecified",
            "systemId": "",
            "primary": True # Explicitly set as primary
        }
        
        current_user_data["posixAccounts"] = [new_posix_account_entry]
        
        read_only_fields = ['kind', 'etag', 'id', 'lastLoginTime', 'creationTime', 
                            'isMailboxSetup', 'isAdmin', 'isDelegatedAdmin', 
                            'agreedToTerms', 'isEnforcedIn2Sv', 'isEnrolledIn2Sv',
                            'deletionTime', '웰म्knownUserAliases', 'customerId', 
                            'orgUnitPath', 'emails', 'aliases', 'nonEditableAliases',
                            'suspended', 'suspensionReason', 'changePasswordAtNextLogin',
                            'ipWhitelisted']
        for field in read_only_fields:
            current_user_data.pop(field, None)
        
        # Ensure essential fields are present if users.update() requires them
        if "primaryEmail" not in current_user_data:
             current_user_data["primaryEmail"] = user_email # Must be present for update

        try:
            print(f"Attempting to update POSIX attributes for {user_email}...")
            self.service.users().update(userKey=user_email, body=current_user_data).execute()
            print(f"Successfully submitted update for {user_email}.")
            return self.verify_update(user_email)
        except HttpError as error:
            print(f'API error updating user {user_email}: {error.resp.status} - {error._get_reason()}')
            print(f"  Error content: {error.content}")
            return False
        except Exception as e:
            print(f'Unexpected error during user update for {user_email}: {e}')
            return False

    def verify_update(self, user_email):
        print(f"Verifying update for {user_email} by fetching fresh data...")
        verified_user_data = self.get_info(user_email, quiet=True)
        if verified_user_data and "posixAccounts" in verified_user_data:
            print(f"  Fresh POSIX Accounts for {user_email}:")
            print(json.dumps(verified_user_data["posixAccounts"], indent=2))
            return True
        elif verified_user_data:
            print(f"  Fresh data fetched for {user_email}, but no 'posixAccounts' array found.")
        else:
            print(f"  Verification failed: Could not fetch fresh data for {user_email}.")
        return False


class GroupManager:
    """Manages GIDs for Google Cloud Identity groups."""
    def __init__(self, service_client):
        self.service = service_client

    def get_info(self, group_email, quiet=False):
        try:
            if not quiet:
                print(f"Fetching current data for group: {group_email}")
            group = self.service.groups().get(groupKey=group_email).execute()
            return group
        except HttpError as error:
            if not quiet:
                print(f'API error fetching group {group_email}: {error.resp.status} - {error._get_reason()}')
            return None

    def update_gid(self, group_email, new_gid):
        group_body_for_patch = {"gid": new_gid}
        try:
            print(f"Attempting to update GID for group {group_email} to {new_gid}...")
            self.service.groups().patch(groupKey=group_email, body=group_body_for_patch).execute()
            print(f"Successfully submitted GID update for {group_email}.")
            return self.verify_update(group_email, new_gid)
        except HttpError as error:
            print(f'API error updating group GID {group_email}: {error.resp.status} - {error._get_reason()}')
            print(f"  Error content: {error.content}")
            return False
        except Exception as e:
            print(f'Unexpected error during group GID update for {group_email}: {e}')
            return False

    def verify_update(self, group_email, expected_gid):
        print(f"Verifying GID update for {group_email} by fetching fresh data...")
        verified_group_data = self.get_info(group_email, quiet=True)
        if verified_group_data and "gid" in verified_group_data:
            print(f"  Fresh GID for {group_email}: {verified_group_data['gid']}")
            if verified_group_data['gid'] != expected_gid:
                print(f"  WARNING: Verification shows GID is {verified_group_data['gid']}, expected {expected_gid}")
            return True
        elif verified_group_data:
            print(f"  Fresh data fetched for group {group_email}, but 'gid' field not found or is None.")
        else:
            print(f"  Verification failed: Could not fetch fresh data for group {group_email}.")
        return False


class PosixAttributeUpdater:
    """Orchestrates POSIX attribute updates for users and groups."""
    def __init__(self, credentials_path, scopes, users_config, groups_config):
        print("Initializing POSIX Attribute Updater...")
        print(f"Using credentials file: {credentials_path}")
        
        self.authenticator = GoogleAdminAuthenticator(credentials_path, scopes)
        self.service_client = self.authenticator.get_service_client()
        
        if not self.service_client:
            print("Failed to get authenticated service. Halting execution.")
            # You might want to raise an exception here or handle it more gracefully
            return

        self.user_manager = UserManager(self.service_client)
        self.group_manager = GroupManager(self.service_client)
        self.users_config = users_config
        self.groups_config = groups_config
        print("Initialization complete. Service client obtained.\n")


    def run_updates(self):
        if not self.service_client:
            print("Cannot run updates: Service client not available.")
            return

        print("--- Processing User POSIX Attribute Updates ---")
        for email, posix_data in self.users_config.items():
            self.user_manager.update_posix_attributes(email, posix_data)
            print("-" * 40)
        
        print("\n--- Processing Group GID Updates ---")
        for group_email, gid_data in self.groups_config.items():
            self.group_manager.update_gid(group_email, gid_data)
            print("-" * 40)
            
        print("\nScript finished.")


if __name__ == '__main__':
    updater = PosixAttributeUpdater(
        CREDENTIALS_JSON_PATH,
        SCOPES,
        USERS_TO_UPDATE_CONFIG,
        GROUPS_TO_UPDATE_CONFIG
    )
    updater.run_updates()
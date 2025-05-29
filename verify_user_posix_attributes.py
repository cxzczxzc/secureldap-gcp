import os
import pickle
import json # For pretty-printing JSON output

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# Full path to your credentials file (ensure this is correct)
CREDENTIALS_JSON_PATH = '/Users/saadx/Documents/PSO/2025/Mayo/OS Login POSIX Groups/posix_attribute_update_app/credentials.json'

# Token file will be stored in the same directory as credentials.json
TOKEN_JSON_PATH = os.path.join(os.path.dirname(CREDENTIALS_JSON_PATH), 'token.json')
TOKEN_PICKLE_PATH = os.path.join(os.path.dirname(CREDENTIALS_JSON_PATH), 'token.pickle') # For legacy token

# SCOPES required for viewing users and groups
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user.readonly',
    'https://www.googleapis.com/auth/admin.directory.group.readonly'
]
API_SERVICE_NAME = 'admin'
API_VERSION = 'directory_v1'

# --- Users and Groups to Fetch ---
USERS_TO_FETCH = [
    "demouser1@saadx.altostrat.com",
    "adminuser1@saadx.altostrat.com",
    "restricteduser1@saadx.altostrat.com" # Add any other users you want to inspect
]

GROUPS_TO_FETCH = [
    "gcp_vm_standard_access@saadx.altostrat.com", # Ensure these are the correct group email addresses
    "gcp_vm_admin_access@saadx.altostrat.com"
]

class GoogleAdminAuthenticator:
    """Handles authentication with Google Admin SDK."""
    def __init__(self, credentials_path, token_path, legacy_token_path, scopes):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.legacy_token_path = legacy_token_path
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

def fetch_and_print_user_json(service, user_email):
    """Fetches a user by email and prints their full JSON object."""
    print(f"\n--- Fetching User: {user_email} ---")
    try:
        # projection='full' gets all attributes including custom schemas.
        # viewType='admin_view' is default, domain_public is less info.
        user_object = service.users().get(userKey=user_email, projection='full').execute()
        print(json.dumps(user_object, indent=2))
    except HttpError as error:
        print(f"Error fetching user {user_email}: {error.resp.status} - {error._get_reason()}")
        print(f"  Error content: {error.content}")
    except Exception as e:
        print(f"An unexpected error occurred fetching user {user_email}: {e}")

def fetch_and_print_group_json(service, group_key):
    """Fetches a group by email or ID and prints its full JSON object."""
    print(f"\n--- Fetching Group: {group_key} ---")
    try:
        group_object = service.groups().get(groupKey=group_key).execute()
        print(json.dumps(group_object, indent=2))
    except HttpError as error:
        print(f"Error fetching group {group_key}: {error.resp.status} - {error._get_reason()}")
        print(f"  Error content: {error.content}")
    except Exception as e:
        print(f"An unexpected error occurred fetching group {group_key}: {e}")


if __name__ == '__main__':
    print("Starting script to fetch user and group JSON...")
    
    authenticator = GoogleAdminAuthenticator(
        CREDENTIALS_JSON_PATH,
        TOKEN_JSON_PATH,
        TOKEN_PICKLE_PATH,
        SCOPES
    )
    service_client = authenticator.get_service_client()

    if service_client:
        print("\nAuthentication successful. Fetching data...\n")

        for user_email_to_fetch in USERS_TO_FETCH:
            fetch_and_print_user_json(service_client, user_email_to_fetch)
            print("-" * 50)
        
        for group_key_to_fetch in GROUPS_TO_FETCH:
            fetch_and_print_group_json(service_client, group_key_to_fetch)
            print("-" * 50)
        
        print("\nScript finished.")
    else:
        print("Failed to get authenticated service. Exiting.")
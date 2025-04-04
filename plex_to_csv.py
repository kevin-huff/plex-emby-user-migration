#!/usr/bin/env python3
import csv
import requests
import urllib.parse
import time
import logging
import argparse
import sys
import os
import json
import random
from io import BytesIO
from base64 import b64encode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('emby_user_creation.log')
    ]
)
logger = logging.getLogger(__name__)

def get_emby_libraries(server_url, api_key):
    """
    Get a list of libraries from the Emby server
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        
    Returns:
        list: List of library dictionaries with id and name
    """
    libraries_url = f"{server_url}/emby/Library/VirtualFolders"
    headers = {
        "X-Emby-Token": api_key
    }
    
    try:
        response = requests.get(libraries_url, headers=headers)
        if response.status_code == 200:
            libraries = response.json()
            return libraries
        else:
            logger.error(f"Failed to get libraries. Status: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Exception getting libraries: {str(e)}")
        return []

def create_user(server_url, api_key, username, email, password, profile_image_url=None, 
                access_libraries=None, default_roles=None):
    """
    Create a new user on Emby server
    
    Args:
        server_url (str): URL of the Emby server (e.g., 'http://localhost:8096')
        api_key (str): Admin API key for Emby
        username (str): Username for the new account
        email (str): Email address for the new account
        password (str): Password for the new account
        profile_image_url (str, optional): URL to user's profile image
        access_libraries (list, optional): List of library IDs to grant access to
        default_roles (list, optional): List of default roles to assign
        
    Returns:
        tuple: (success (bool), user_id or error message (str))
    """
    # Step 1: Create the user
    create_user_url = f"{server_url}/emby/Users/New"
    headers = {
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    
    # Prepare default roles if not provided
    if default_roles is None:
        default_roles = ["EnablePlayback", "EnableMediaPlayback", "EnableSharedDeviceControl", "EnableVideoPlayback", "EnableAudioPlayback"]
    
    user_data = {
        "Name": username,
        "Email": email,
        "Password": password
    }
    
    try:
        response = requests.post(create_user_url, headers=headers, json=user_data)
        
        if response.status_code == 200 or response.status_code == 204:
            user_id = None
            try:
                user_id = response.json().get('Id')
            except ValueError:
                # Find the user ID by looking up the username
                user_id = get_user_id_by_name(server_url, api_key, username)
                
            if not user_id:
                logger.error(f"Failed to get user ID for {username}")
                return False, "Could not retrieve user ID"
                
            logger.info(f"Successfully created user: {username} with ID: {user_id}")
            
            # Step 2: Set user policy including roles
            policy_success = set_user_policy(server_url, api_key, user_id, default_roles)
            if not policy_success:
                logger.warning(f"Failed to set policy for user {username}")
            
            # Step 3: Set library access
            if access_libraries:
                access_success = set_library_access(server_url, api_key, user_id, access_libraries)
                if not access_success:
                    logger.warning(f"Failed to set library access for user {username}")
            
            # Step 4: If profile image URL is provided, set the profile image
            if profile_image_url:
                upload_profile_image(server_url, api_key, user_id, profile_image_url)
                
            return True, user_id
        else:
            error_msg = f"Failed to create user {username}. Status code: {response.status_code}, Response: {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Exception creating user {username}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_user_id_by_name(server_url, api_key, username):
    """
    Get a user's ID by their username
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        username (str): Username to look up
        
    Returns:
        str: User ID or None if not found
    """
    users_url = f"{server_url}/emby/Users"
    headers = {
        "X-Emby-Token": api_key
    }
    
    try:
        response = requests.get(users_url, headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get('Name') == username:
                    return user.get('Id')
        return None
    except Exception as e:
        logger.error(f"Exception getting user ID: {str(e)}")
        return None

def set_user_policy(server_url, api_key, user_id, roles):
    """
    Set policy and roles for a user
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        user_id (str): ID of the user to update
        roles (list): List of role IDs to assign
        
    Returns:
        bool: Success or failure
    """
    policy_url = f"{server_url}/emby/Users/{user_id}/Policy"
    headers = {
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    
    # Default policy settings that match standard user permissions
    policy_data = {
        "IsAdministrator": False,
        "IsHidden": False,
        "IsDisabled": False,
        "BlockedTags": [],
        "EnableUserPreferenceAccess": True,
        "AccessSchedules": [],
        "BlockUnratedItems": [],
        "EnableRemoteControlOfOtherUsers": False,
        "EnableSharedDeviceControl": True,
        "EnableRemoteAccess": True,
        "EnableLiveTvManagement": False,
        "EnableLiveTvAccess": True,
        "EnableMediaPlayback": True,
        "EnableAudioPlaybackTranscoding": True,
        "EnableVideoPlaybackTranscoding": True,
        "EnablePlaybackRemuxing": True,
        "EnablePublicSharing": False,
        "EnableDownloading": True,
        "EnableSubtitleDownloading": True,
        "EnableSubtitleManagement": False,
        "EnableSyncTranscoding": True,
        "EnableMediaConversion": True,
        "EnableAllDevices": True,
        "EnableAllChannels": False,
        "EnableRemoteControllers": True
    }
    
    # Add specific roles
    for role in roles:
        if role == "EnablePlayback":
            policy_data["EnableMediaPlayback"] = True
        elif role == "EnableVideoPlayback":
            policy_data["EnableVideoPlaybackTranscoding"] = True
        elif role == "EnableAudioPlayback":
            policy_data["EnableAudioPlaybackTranscoding"] = True
        # Add more role mappings as needed
    
    try:
        response = requests.post(policy_url, headers=headers, json=policy_data)
        return response.status_code == 200 or response.status_code == 204
    except Exception as e:
        logger.error(f"Exception setting user policy: {str(e)}")
        return False

def set_library_access(server_url, api_key, user_id, library_ids):
    """
    Set library access permissions for a user
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        user_id (str): ID of the user to update
        library_ids (list): List of library IDs to grant access to
        
    Returns:
        bool: Success or failure
    """
    url = f"{server_url}/emby/Users/{user_id}/Policy"
    headers = {
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    
    # First get the current policy
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get user policy. Status: {response.status_code}")
            return False
            
        policy = response.json()
        
        # Update the policy with library access
        if "EnableAllFolders" in policy:
            policy["EnableAllFolders"] = False
        
        policy["EnabledFolders"] = library_ids
        
        # Update the policy
        update_response = requests.post(url, headers=headers, json=policy)
        return update_response.status_code == 200 or update_response.status_code == 204
        
    except Exception as e:
        logger.error(f"Exception setting library access: {str(e)}")
        return False

def get_random_avatar():
    """
    Get a random avatar image from a public API
    
    Returns:
        bytes or None: The image data or None if failed
    """
    # List of APIs that provide random avatar images
    random_avatar_apis = [
        "https://api.dicebear.com/7.x/adventurer/svg",
        "https://api.dicebear.com/7.x/bottts/svg",
        "https://api.dicebear.com/7.x/fun-emoji/svg",
        "https://api.dicebear.com/7.x/pixel-art/svg"
    ]
    
    try:
        # Select a random API
        api_url = random.choice(random_avatar_apis)
        # Add a random seed to get different images
        seed = f"seed={random.randint(1, 10000)}"
        url = f"{api_url}?{seed}"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            logger.warning(f"Failed to get random avatar. Status: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Exception getting random avatar: {str(e)}")
        return None

def upload_profile_image(server_url, api_key, user_id, image_url):
    """
    Upload a profile image for a user from a URL
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        user_id (str): ID of the user to update
        image_url (str): URL of the image to use as profile picture
    """
    try:
        # First, try to download the image from the URL
        image_data = None
        content_type = None
        
        try:
            image_response = requests.get(image_url, timeout=10)
            if image_response.status_code == 200:
                image_data = image_response.content
                content_type = image_response.headers.get('Content-Type', 'image/jpeg')
            else:
                logger.warning(f"Failed to download profile image from {image_url}. Status: {image_response.status_code}")
        except Exception as e:
            logger.warning(f"Error downloading profile image from URL: {str(e)}")
            
        # If original image download failed, get a random avatar
        if not image_data:
            logger.info(f"Using random avatar for user ID: {user_id}")
            image_data = get_random_avatar()
            content_type = 'image/svg+xml'
            
        if not image_data:
            logger.warning(f"Could not get any profile image for user ID: {user_id}")
            return
            
        # Now upload the image to Emby
        upload_url = f"{server_url}/emby/Users/{user_id}/Images/Primary"
        headers = {
            "X-Emby-Token": api_key,
            "Content-Type": content_type
        }
        
        upload_response = requests.post(
            upload_url, 
            headers=headers,
            data=image_data
        )
        
        if upload_response.status_code == 200 or upload_response.status_code == 204:
            logger.info(f"Successfully uploaded profile image for user ID: {user_id}")
        else:
            logger.warning(f"Failed to upload profile image for user ID: {user_id}. Status: {upload_response.status_code}")
            
    except Exception as e:
        logger.error(f"Exception uploading profile image: {str(e)}")

def process_csv(csv_file, server_url, api_key, libraries=None, default_roles=None, dry_run=False, delay=1):
    """
    Process a CSV file containing user data and create users on Emby server
    
    Args:
        csv_file (str): Path to the CSV file
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        libraries (list, optional): List of library IDs to grant access to
        default_roles (list, optional): List of default roles to assign
        dry_run (bool): If True, only print what would be done without actually creating users
        delay (int): Delay in seconds between API calls to avoid rate limiting
    """
    successful_users = 0
    failed_users = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Verify required columns exist
        required_columns = ["Username", "Email", "Passphrase"]
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        
        if missing_columns:
            logger.error(f"CSV is missing required columns: {', '.join(missing_columns)}")
            return
            
        for row in reader:
            username = row["Username"]
            email = row["Email"]
            password = row["Passphrase"]
            thumb_url = row.get("Thumb", None)
            
            # Log the user we're about to create
            if dry_run:
                logger.info(f"[DRY RUN] Would create user: {username}, Email: {email}, Libraries: {libraries}")
                successful_users += 1
                continue
                
            # Create the user on Emby
            success, result = create_user(
                server_url, 
                api_key, 
                username, 
                email, 
                password, 
                thumb_url, 
                libraries, 
                default_roles
            )
            
            if success:
                successful_users += 1
            else:
                failed_users += 1
                
            # Add delay between requests to avoid rate limiting
            if delay > 0:
                time.sleep(delay)
    
    logger.info(f"User creation complete. Successful: {successful_users}, Failed: {failed_users}")

def list_and_select_libraries(server_url, api_key, selected_libraries=None):
    """
    List all libraries on the Emby server and let the user select which ones to grant access to
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        selected_libraries (list, optional): List of pre-selected library IDs
        
    Returns:
        list: List of selected library IDs
    """
    libraries = get_emby_libraries(server_url, api_key)
    
    if not libraries:
        logger.error("Could not retrieve libraries from Emby server")
        return []
        
    logger.info("Available libraries:")
    for i, lib in enumerate(libraries, 1):
        logger.info(f"{i}. {lib.get('Name')} (ID: {lib.get('ItemId')})")
        
    if selected_libraries == "all":
        logger.info("All libraries selected")
        return [lib.get('ItemId') for lib in libraries]
        
    if selected_libraries:
        # Check if selected_libraries is a comma-separated string of IDs
        if isinstance(selected_libraries, str):
            selected_ids = selected_libraries.split(',')
            # Validate IDs
            valid_ids = [lib.get('ItemId') for lib in libraries]
            return [lib_id for lib_id in selected_ids if lib_id in valid_ids]
        return selected_libraries
        
    # Interactive selection
    try:
        selection = input("Enter library numbers to grant access to (comma-separated, 'all' for all): ")
        if selection.lower() == 'all':
            return [lib.get('ItemId') for lib in libraries]
            
        selected_indexes = [int(idx.strip()) - 1 for idx in selection.split(',')]
        return [libraries[idx].get('ItemId') for idx in selected_indexes if 0 <= idx < len(libraries)]
    except Exception as e:
        logger.error(f"Error during library selection: {str(e)}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Emby users from a CSV file")
    parser.add_argument("csv_file", help="Path to CSV file with user data")
    parser.add_argument("--server", required=True, help="Emby server URL (e.g., http://localhost:8096)")
    parser.add_argument("--api-key", required=True, help="Emby admin API key")
    parser.add_argument("--libraries", help="Library IDs to grant access to (comma-separated, or 'all')")
    parser.add_argument("--roles", help="Default roles to assign (comma-separated)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without creating users")
    parser.add_argument("--delay", type=int, default=1, help="Delay in seconds between API calls (default: 1)")
    parser.add_argument("--list-libraries", action="store_true", help="List available libraries and exit")
    
    args = parser.parse_args()
    
    # List libraries and exit if requested
    if args.list_libraries:
        list_and_select_libraries(args.server, args.api_key)
        sys.exit(0)
        
    if not os.path.exists(args.csv_file):
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)
        
    # Set default roles
    default_roles = [
        "EnablePlayback",
        "EnableMediaPlayback", 
        "EnableSharedDeviceControl", 
        "EnableVideoPlayback", 
        "EnableAudioPlayback"
    ]
    
    if args.roles:
        default_roles = args.roles.split(',')
        
    # Get library access
    selected_libraries = None
    if args.libraries:
        if args.libraries.lower() == 'all':
            selected_libraries = "all"
        else:
            selected_libraries = args.libraries.split(',')
    
    # Interactive selection if no libraries specified
    if selected_libraries is None and not args.dry_run:
        selected_libraries = list_and_select_libraries(args.server, args.api_key)
        
    logger.info(f"Starting Emby user creation from CSV: {args.csv_file}")
    logger.info(f"Server URL: {args.server}")
    logger.info(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    logger.info(f"Selected libraries: {selected_libraries}")
    logger.info(f"Default roles: {default_roles}")
    
    process_csv(
        args.csv_file, 
        args.server, 
        args.api_key, 
        selected_libraries, 
        default_roles, 
        args.dry_run, 
        args.delay
    )
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
import string
import hashlib
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
    Get a list of libraries from the Emby server - optimized for Emby 4.8.11.0
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        
    Returns:
        list: List of library dictionaries with id and name
    """
    # For Emby 4.8.11.0, the most reliable endpoint for libraries
    libraries_url = f"{server_url}/emby/Library/MediaFolders"
    headers = {
        "X-Emby-Token": api_key
    }
    
    try:
        logger.info(f"Fetching libraries from {libraries_url}")
        response = requests.get(libraries_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Emby 4.8.11.0 returns a structure with 'Items' array
            if 'Items' in data and isinstance(data['Items'], list):
                libraries = data['Items']
                normalized_libraries = []
                
                for lib in libraries:
                    lib_id = lib.get('Id')
                    lib_name = lib.get('Name')
                    
                    if lib_id and lib_name:
                        normalized_libraries.append({
                            'ItemId': lib_id,
                            'Name': lib_name
                        })
                
                logger.info(f"Found {len(normalized_libraries)} libraries")
                return normalized_libraries
            else:
                logger.warning("Unexpected library data format")
        else:
            logger.error(f"Failed to get libraries. Status: {response.status_code}")
            
        # Fallback to a second endpoint if the first one failed
        fallback_url = f"{server_url}/emby/Library/VirtualFolders"
        logger.info(f"Trying fallback library endpoint: {fallback_url}")
        
        fallback_response = requests.get(fallback_url, headers=headers)
        if fallback_response.status_code == 200:
            libraries = fallback_response.json()
            normalized_libraries = []
            
            for lib in libraries:
                lib_id = lib.get('ItemId') or lib.get('Id')
                lib_name = lib.get('Name')
                
                if lib_id and lib_name:
                    normalized_libraries.append({
                        'ItemId': lib_id,
                        'Name': lib_name
                    })
            
            logger.info(f"Found {len(normalized_libraries)} libraries using fallback endpoint")
            return normalized_libraries
            
        logger.warning("Failed to get libraries from fallback endpoint")
            
    except Exception as e:
        logger.error(f"Exception getting libraries: {str(e)}")
    
    # Create a fallback of 1 fake library
    fallback_library = [{
        'ItemId': 'all',
        'Name': 'All Libraries (Fallback)'
    }]
    logger.warning("Using fallback library option")
    return fallback_library

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
            
            # Add a delay after user creation before setting policies
            time.sleep(1)
            
            # Step 2: Set user policy including roles
            if default_roles:
                policy_success = set_user_policy(server_url, api_key, user_id, default_roles)
                if not policy_success:
                    logger.warning(f"Failed to set policy for user {username}")
            
            # Step 3: Set library access
            if access_libraries:
                # Add a delay before setting library access
                time.sleep(1)
                access_success = set_library_access(server_url, api_key, user_id, access_libraries)
                if not access_success:
                    logger.warning(f"Failed to set library access for user {username}")
            
            # Step 4: If profile image URL is provided, set the profile image
            if profile_image_url:
                # Add a delay before setting profile image
                time.sleep(1)
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
    Set library access permissions for a user - optimized for Emby 4.8.11.0
    
    Args:
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
        user_id (str): ID of the user to update
        library_ids (list): List of library IDs to grant access to
        
    Returns:
        bool: Success or failure
    """
    # For Emby 4.8.11.0, the user policy endpoint appears to be using this path
    url = f"{server_url}/emby/Users/{user_id}/Policy"
    headers = {
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    
    # First get the current policy
    try:
        logger.info(f"Fetching current policy for user ID: {user_id}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get user policy. Status: {response.status_code}")
            
            # Let's try an alternative approach by directly setting EnableAllFolders
            # without first fetching the policy
            if library_ids == "all":
                direct_policy = {
                    "EnableAllFolders": True,
                    "EnableAllChannels": False,
                    "EnableAllDevices": True,
                    "EnableContentDeletion": False,
                    "EnableSync": True,
                    "EnableLiveTvAccess": False,
                    "EnableLiveTvManagement": False,
                    "EnableMediaPlayback": True,
                    "EnableAudioPlaybackTranscoding": True,
                    "EnableVideoPlaybackTranscoding": True,
                    "EnablePlaybackRemuxing": True,
                    "EnableSharedDeviceControl": True
                }
                
                direct_url = f"{server_url}/emby/Users/{user_id}/Policy"
                try:
                    direct_response = requests.post(direct_url, headers=headers, json=direct_policy)
                    if direct_response.status_code == 200 or direct_response.status_code == 204:
                        logger.info(f"Successfully set EnableAllFolders=true policy for user ID: {user_id}")
                        return True
                    else:
                        logger.error(f"Failed to set direct policy. Status: {direct_response.status_code}")
                except Exception as e:
                    logger.error(f"Exception setting direct policy: {str(e)}")
            
            return False
            
        policy = response.json()
        logger.info(f"Successfully retrieved current policy for user ID: {user_id}")
        
        # Make a copy of the policy to modify
        updated_policy = policy.copy()
        
        # Update the policy with library access
        if library_ids == "all":
            updated_policy["EnableAllFolders"] = True
        else:
            updated_policy["EnableAllFolders"] = False
            if "EnabledFolders" in updated_policy:
                updated_policy["EnabledFolders"] = library_ids
        
        # Ensure these settings are enabled for general access
        updated_policy["EnableMediaPlayback"] = True
        updated_policy["EnableAudioPlaybackTranscoding"] = True
        updated_policy["EnableVideoPlaybackTranscoding"] = True
        updated_policy["EnablePlaybackRemuxing"] = True
        updated_policy["EnableSharedDeviceControl"] = True
        
        # Log the changes we're making
        logger.info(f"Setting EnableAllFolders={updated_policy['EnableAllFolders']} for user ID: {user_id}")
        
        # Update the policy
        update_response = requests.post(url, headers=headers, json=updated_policy)
        status = update_response.status_code
        
        if status == 200 or status == 204:
            logger.info(f"Successfully updated policy for user ID: {user_id}")
            return True
        else:
            logger.error(f"Failed to update policy. Status: {status}, Response: {update_response.text}")
            return False
        
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
    try:
        # First try DiceBear APIs which provide SVGs
        random_avatar_apis = [
            "https://api.dicebear.com/7.x/adventurer/svg",
            "https://api.dicebear.com/7.x/bottts/svg",
            "https://api.dicebear.com/7.x/fun-emoji/svg",
            "https://api.dicebear.com/7.x/pixel-art/svg"
        ]
        
        # Select a random API
        api_url = random.choice(random_avatar_apis)
        # Add a random seed to get different images
        seed = f"seed={random.randint(1, 10000)}"
        url = f"{api_url}?{seed}"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.warning(f"Error getting random SVG avatar: {str(e)}")
    
    # Fall back to Gravatar-style image which might be more compatible
    try:
        # Generate a random hash for Gravatar-style image
        gravatar_hash = ''.join(random.choices(string.hexdigits.lower(), k=32))
        url = f"https://www.gravatar.com/avatar/{gravatar_hash}?d=identicon&s=200"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.warning(f"Error getting Gravatar avatar: {str(e)}")
    
    # Last resort - create a simple colored square as PNG
    try:
        import io
        from PIL import Image
        
        # Create a simple image - a colored square
        size = 200
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        image = Image.new('RGB', (size, size), color)
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except ImportError:
        logger.warning("PIL not available for fallback image generation")
    except Exception as e:
        logger.warning(f"Error creating fallback image: {str(e)}")
    
    logger.warning("All avatar generation methods failed")
    return None

def upload_profile_image(server_url, api_key, user_id, image_url):
    """
    Upload a profile image for a user from a URL - optimized for Emby 4.8.11.0
    
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
        
        # Attempt to download the Plex image with proper headers
        try:
            # Plex URLs often need a proper user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            logger.info(f"Downloading image from URL: {image_url}")
            image_response = requests.get(image_url, headers=headers, timeout=10)
            
            if image_response.status_code == 200:
                image_data = image_response.content
                content_type = image_response.headers.get('Content-Type', 'image/jpeg')
                logger.info(f"Successfully downloaded image ({len(image_data)} bytes, type: {content_type})")
            else:
                logger.warning(f"Failed to download profile image from {image_url}. Status: {image_response.status_code}")
        except Exception as e:
            logger.warning(f"Error downloading profile image from URL: {str(e)}")
        
        # If can't get the Plex image, fallback to Gravatar which has better compatibility
        if not image_data:
            try:
                # Generate a random hash for Gravatar
                email_hash = hashlib.md5(f"{user_id}@example.com".encode('utf-8')).hexdigest()
                gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=200"
                
                logger.info(f"Falling back to Gravatar image: {gravatar_url}")
                gravatar_response = requests.get(gravatar_url, timeout=10)
                
                if gravatar_response.status_code == 200:
                    image_data = gravatar_response.content
                    content_type = gravatar_response.headers.get('Content-Type', 'image/jpeg')
                    logger.info(f"Successfully downloaded Gravatar image ({len(image_data)} bytes)")
                else:
                    logger.warning(f"Failed to download Gravatar. Status: {gravatar_response.status_code}")
            except Exception as e:
                logger.warning(f"Error with Gravatar fallback: {str(e)}")
        
        if not image_data:
            logger.warning(f"Could not get any profile image for user ID: {user_id}")
            return
        
        # Based on the error, Emby 4.8.11.0 expects base64-encoded image data
        try:
            # Base64 encode the image data
            b64_data = b64encode(image_data).decode('utf-8')
            
            upload_url = f"{server_url}/emby/Users/{user_id}/Images/Primary"
            headers = {
                "X-Emby-Token": api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Uploading profile image for user ID: {user_id} using base64 encoding")
            
            # Extract format from content type (e.g., "image/png" -> "png")
            format_type = content_type.split('/')[-1] if content_type else "jpeg"
            
            # Create the JSON payload with base64 data
            payload = {
                "Format": format_type,
                "Data": b64_data
            }
            
            upload_response = requests.post(
                upload_url, 
                headers=headers,
                json=payload
            )
            
            if upload_response.status_code == 200 or upload_response.status_code == 204:
                logger.info(f"Successfully uploaded profile image for user ID: {user_id}")
                return
            else:
                logger.warning(f"Failed to upload profile image. Status: {upload_response.status_code}, Response: {upload_response.text}")
                
                # Try alternative upload method with simpler payload
                logger.info("Trying alternative base64 upload method")
                
                alt_upload_url = f"{server_url}/emby/Items/{user_id}/Images/Primary"
                alt_response = requests.post(
                    alt_upload_url,
                    headers=headers,
                    json={"data": b64_data}
                )
                
                if alt_response.status_code == 200 or alt_response.status_code == 204:
                    logger.info(f"Successfully uploaded profile image using alternative method for user ID: {user_id}")
                    return
                else:
                    logger.warning(f"Alternative upload also failed. Status: {alt_response.status_code}")
                    
        except Exception as e:
            logger.error(f"Exception uploading profile image: {str(e)}")
            
    except Exception as e:
        logger.error(f"Exception in profile image handling: {str(e)}")

def process_csv(csv_file, server_url, api_key, libraries=None, default_roles=None, dry_run=False, delay=1, skip_libraries=False, skip_images=False):
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
        skip_libraries (bool): If True, skip library access setting
        skip_images (bool): If True, skip profile image uploads
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
                thumb_url if not skip_images else None, 
                libraries if not skip_libraries else None, 
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
    parser.add_argument("--skip-libraries", action="store_true", help="Skip setting library access")
    parser.add_argument("--skip-images", action="store_true", help="Skip profile image uploads")
    parser.add_argument("--test-connection", action="store_true", help="Test connection to Emby server and exit")
    
    args = parser.parse_args()
    
    # For Emby 4.8.11.0, we're having issues with image uploads, so automatically skip them
    args.skip_images = True
    logger.info("Automatically skipping profile image uploads due to compatibility with Emby 4.8.11.0")
    
    # Test connection to Emby server
    if args.test_connection:
        try:
            test_url = f"{args.server}/emby/System/Info"
            headers = {"X-Emby-Token": args.api_key}
            response = requests.get(test_url, headers=headers)
            if response.status_code == 200:
                server_info = response.json()
                logger.info(f"Successfully connected to Emby server:")
                logger.info(f"  Version: {server_info.get('Version', 'Unknown')}")
                logger.info(f"  Server Name: {server_info.get('ServerName', 'Unknown')}")
                logger.info(f"  Operating System: {server_info.get('OperatingSystem', 'Unknown')}")
            else:
                logger.error(f"Connection failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
        sys.exit(0)
    
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
    if not args.skip_libraries:
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
    if args.skip_libraries:
        logger.info("Library access setting will be skipped")
    else:
        logger.info(f"Selected libraries: {selected_libraries}")
    if args.skip_images:
        logger.info("Profile image uploads will be skipped")
    logger.info(f"Default roles: {default_roles}")
    
    process_csv(
        args.csv_file, 
        args.server, 
        args.api_key, 
        selected_libraries, 
        default_roles, 
        args.dry_run, 
        args.delay,
        args.skip_libraries,
        args.skip_images
    )
#!/usr/bin/env python3
import csv
import requests
import urllib.parse
import time
import logging
import argparse
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('emby_user_creation.log')
    ]
)
logger = logging.getLogger(__name__)

def create_user(server_url, api_key, username, email, password, profile_image_url=None):
    """
    Create a new user on Emby server
    
    Args:
        server_url (str): URL of the Emby server (e.g., 'http://localhost:8096')
        api_key (str): Admin API key for Emby
        username (str): Username for the new account
        email (str): Email address for the new account
        password (str): Password for the new account
        profile_image_url (str, optional): URL to user's profile image
        
    Returns:
        tuple: (success (bool), user_id or error message (str))
    """
    # Step 1: Create the user
    create_user_url = f"{server_url}/emby/Users/New"
    headers = {
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    
    user_data = {
        "Name": username,
        "Email": email,
        "Password": password
    }
    
    try:
        response = requests.post(create_user_url, headers=headers, json=user_data)
        
        if response.status_code == 200 or response.status_code == 204:
            logger.info(f"Successfully created user: {username}")
            user_id = response.json().get('Id')
            
            # Step 2: If profile image URL is provided, set the profile image
            if profile_image_url and user_id:
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
        # First, download the image from the URL
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            logger.warning(f"Failed to download profile image from {image_url}")
            return
            
        # Now upload the image to Emby
        upload_url = f"{server_url}/emby/Users/{user_id}/Images/Primary"
        headers = {
            "X-Emby-Token": api_key,
            "Content-Type": image_response.headers.get('Content-Type', 'image/jpeg')
        }
        
        upload_response = requests.post(
            upload_url, 
            headers=headers,
            data=image_response.content
        )
        
        if upload_response.status_code == 200 or upload_response.status_code == 204:
            logger.info(f"Successfully uploaded profile image for user ID: {user_id}")
        else:
            logger.warning(f"Failed to upload profile image for user ID: {user_id}. Status: {upload_response.status_code}")
            
    except Exception as e:
        logger.error(f"Exception uploading profile image: {str(e)}")

def process_csv(csv_file, server_url, api_key, dry_run=False, delay=1):
    """
    Process a CSV file containing user data and create users on Emby server
    
    Args:
        csv_file (str): Path to the CSV file
        server_url (str): URL of the Emby server
        api_key (str): Admin API key for Emby
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
                logger.info(f"[DRY RUN] Would create user: {username}, Email: {email}")
                successful_users += 1
                continue
                
            # Create the user on Emby
            success, result = create_user(server_url, api_key, username, email, password, thumb_url)
            
            if success:
                successful_users += 1
            else:
                failed_users += 1
                
            # Add delay between requests to avoid rate limiting
            if delay > 0:
                time.sleep(delay)
    
    logger.info(f"User creation complete. Successful: {successful_users}, Failed: {failed_users}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Emby users from a CSV file")
    parser.add_argument("csv_file", help="Path to CSV file with user data")
    parser.add_argument("--server", required=True, help="Emby server URL (e.g., http://localhost:8096)")
    parser.add_argument("--api-key", required=True, help="Emby admin API key")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without creating users")
    parser.add_argument("--delay", type=int, default=1, help="Delay in seconds between API calls (default: 1)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)
        
    logger.info(f"Starting Emby user creation from CSV: {args.csv_file}")
    logger.info(f"Server URL: {args.server}")
    logger.info(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    
    process_csv(args.csv_file, args.server, args.api_key, args.dry_run, args.delay)
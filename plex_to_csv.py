#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import csv
import random
import secrets
import string
import argparse
import sys
import os
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('plex_to_csv.log')
    ]
)
logger = logging.getLogger(__name__)

def generate_passphrase(word_list=None, min_words=3, separator_choices=None, include_number=True):
    """
    Generate a random passphrase
    
    Args:
        word_list (list, optional): List of words to use for the passphrase
        min_words (int, optional): Minimum number of words to include
        separator_choices (list, optional): List of separators to choose from
        include_number (bool, optional): Whether to include a random number
        
    Returns:
        str: The generated passphrase
    """
    # Default word list if none provided
    if word_list is None:
        word_list = [
            "fart", "toot", "poot", "fluff", "bootybomb", 
            "bottomburp", "stinker", "gas", "flatulence", "windypop",
            "buttburp", "trousercough", "blast", "rearbreeze", "stinkbomb",
            "bootytooty", "poop", "doodoo", "caca", "doody", 
            "numbertwo", "dump", "plop", "stinky", "toilet",
            "potty", "flush", "weewee", "peepee", "tinkle",
            "piddle", "whiz", "numberone", "pee", "butt",
            "bottom", "tushy", "bum", "hiney", "tooshie",
            "rump", "burp", "belch", "booger", "snot",
            "undies", "wedgie", "skidmark", "dingleberry", "porcelainthrone"
        ]
    
    # Default separator choices if none provided
    if separator_choices is None:
        separator_choices = ['_', '+', '-']
    
    # Ensure the word list has at least the minimum number of words
    if len(word_list) < min_words:
        raise ValueError(f"Word list must contain at least {min_words} words.")
    
    # Randomly select distinct words
    words = random.sample(word_list, min_words)
    
    # Choose a random separator from the specified options
    separator = random.choice(separator_choices)
    
    # Generate a random number between 0 and 99 if requested
    if include_number:
        number = str(secrets.randbelow(100))
        
        # Insert the number at a random position among the words
        insert_position = random.randint(0, min_words)
        words.insert(insert_position, number)
    
    # Join the words with the chosen separator to form the passphrase
    passphrase = separator.join(words)
    
    return passphrase

def extract_users_from_xml(xml_file, csv_file, custom_word_list=None, dry_run=False):
    """
    Extract user data from XML and write to CSV with generated passphrases
    
    Args:
        xml_file (str): Path to the XML file
        csv_file (str): Path to the output CSV file
        custom_word_list (list, optional): Custom word list for passphrases
        dry_run (bool): If True, only show what would be done without writing to file
    """
    try:
        logger.info(f"Reading XML file: {xml_file}")
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error(f"XML file not found: {xml_file}")
        sys.exit(1)
        
    # Check for alternative XML structures
    user_elements = []
    
    # Try common structures in Plex XML exports
    possible_paths = [
        './User',           # Direct children
        './users/User',     # Nested under 'users'
        './MediaContainer/User',  # Nested under MediaContainer
        './/User'           # Any User element anywhere (fallback)
    ]
    
    for path in possible_paths:
        found_users = root.findall(path)
        if found_users:
            user_elements = found_users
            logger.info(f"Found {len(user_elements)} users using path: {path}")
            break
    
    if not user_elements:
        logger.error("No users found in the XML file. The XML structure may not be supported.")
        # Print the first few lines of the XML for debugging
        xml_content = ET.tostring(root, encoding='utf-8').decode('utf-8')[:500]
        logger.info(f"XML preview: {xml_content}...")
        sys.exit(1)
    
    # Extract user data
    users_data = []
    for user in user_elements:
        user_data = {}
        
        # Try different attribute names for user data (Plex API can vary)
        for id_attr in ['id', 'ratingKey', 'key']:
            if user.get(id_attr):
                user_data['ID'] = user.get(id_attr)
                break
        
        # Try different attribute names for username
        for name_attr in ['username', 'title', 'name']:
            if user.get(name_attr):
                user_data['Username'] = user.get(name_attr)
                break
        
        # Get email
        user_data['Email'] = user.get('email', '')
        
        # Get thumbnail URL
        for thumb_attr in ['thumb', 'thumbUrl', 'avatar']:
            if user.get(thumb_attr):
                user_data['Thumb'] = user.get(thumb_attr)
                break
        
        # Get roles if available
        user_data['Roles'] = user.get('roles', '')
        
        # Generate a random passphrase
        user_data['Passphrase'] = generate_passphrase(custom_word_list)
        
        users_data.append(user_data)
    
    # Sort users by username
    users_data.sort(key=lambda x: x.get('Username', '').lower())
    
    # For dry run, just print what would be done
    if dry_run:
        logger.info(f"DRY RUN: Would write {len(users_data)} users to {csv_file}")
        for idx, user in enumerate(users_data[:5], 1):
            logger.info(f"User {idx}: {user.get('Username', 'Unknown')} - {user.get('Email', 'No Email')} - Passphrase: {user.get('Passphrase', 'None')}")
        if len(users_data) > 5:
            logger.info(f"...and {len(users_data) - 5} more users")
        return
    
    # Write to CSV
    try:
        # Determine which fields we have data for
        all_fields = set()
        for user in users_data:
            all_fields.update(user.keys())
        
        # Ensure required fields are first in order
        required_fields = ['ID', 'Username', 'Email', 'Thumb', 'Roles', 'Passphrase']
        fieldnames = [f for f in required_fields if f in all_fields]
        
        # Add any other fields that might be present
        fieldnames.extend(sorted([f for f in all_fields if f not in required_fields]))
        
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(users_data)
            
        logger.info(f"Successfully wrote {len(users_data)} users to {csv_file}")
    except Exception as e:
        logger.error(f"Error writing to CSV file: {e}")
        sys.exit(1)

def load_custom_word_list(word_list_file):
    """
    Load a custom word list from a file
    
    Args:
        word_list_file (str): Path to the word list file
        
    Returns:
        list: List of words
    """
    try:
        with open(word_list_file, 'r', encoding='utf-8') as f:
            # Read words, stripping whitespace and ignoring empty lines
            words = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(words)} words from {word_list_file}")
        return words
    except Exception as e:
        logger.error(f"Error loading word list: {e}")
        return None

def create_sample_word_list(output_file):
    """
    Create a sample word list file
    
    Args:
        output_file (str): Path to save the word list file
    """
    # Default word list that's easy to read over the phone/written down
    sample_words = [
        "apple", "banana", "carrot", "dolphin", "elephant",
        "forest", "guitar", "house", "island", "jungle",
        "kiwi", "lemon", "mountain", "notebook", "orange",
        "pencil", "queen", "robot", "sunset", "table",
        "umbrella", "violin", "window", "xylophone", "yogurt",
        "zebra", "airplane", "balloon", "castle", "diamond",
        "eagle", "flower", "garden", "hammer", "igloo",
        "jacket", "kingdom", "lantern", "magnet", "noodle",
        "ocean", "planet", "quilt", "rainbow", "scissors",
        "tiger", "unicorn", "village", "wallet", "yo-yo"
    ]
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Custom word list for passphrases\n")
            f.write("# Each line contains one word\n")
            f.write("# Empty lines and lines starting with # are ignored\n\n")
            
            for word in sample_words:
                f.write(f"{word}\n")
        
        logger.info(f"Created sample word list at {output_file}")
        logger.info("Edit this file to customize your passphrase words")
    except Exception as e:
        logger.error(f"Error creating word list file: {e}")

def display_users_preview(xml_file, count=5):
    """
    Display a preview of users from the XML file
    
    Args:
        xml_file (str): Path to the XML file
        count (int): Number of users to preview
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Try common structures in Plex XML exports
        possible_paths = [
            './User',
            './users/User',
            './MediaContainer/User',
            './/User'
        ]
        
        user_elements = []
        for path in possible_paths:
            found_users = root.findall(path)
            if found_users:
                user_elements = found_users
                break
        
        if not user_elements:
            logger.error("No users found in the XML file.")
            return
        
        logger.info(f"Found {len(user_elements)} users in {xml_file}")
        logger.info(f"Showing preview of first {min(count, len(user_elements))} users:")
        
        for i, user in enumerate(user_elements[:count], 1):
            username = user.get('username') or user.get('title') or user.get('name') or 'Unknown'
            email = user.get('email') or 'No Email'
            user_id = user.get('id') or user.get('ratingKey') or user.get('key') or 'No ID'
            
            logger.info(f"User {i}: ID={user_id}, Username={username}, Email={email}")
            
        if len(user_elements) > count:
            logger.info(f"...and {len(user_elements) - count} more users")
            
    except Exception as e:
        logger.error(f"Error previewing XML: {e}")

def generate_test_passphrases(word_list_file=None, count=10):
    """
    Generate and display test passphrases
    
    Args:
        word_list_file (str, optional): Path to custom word list file
        count (int): Number of passphrases to generate
    """
    custom_words = None
    if word_list_file:
        custom_words = load_custom_word_list(word_list_file)
    
    logger.info(f"Generating {count} sample passphrases:")
    for i in range(count):
        passphrase = generate_passphrase(custom_words)
        logger.info(f"  {i+1}. {passphrase}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Plex users XML to CSV with generated passphrases")
    parser.add_argument("--xml", help="Path to Plex users XML file")
    parser.add_argument("--csv", default="users.csv", help="Path for output CSV file (default: users.csv)")
    parser.add_argument("--word-list", help="Path to custom word list file for passphrases")
    parser.add_argument("--create-word-list", help="Create a sample word list file at specified path and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing to file")
    parser.add_argument("--preview", help="Preview users in the XML file without generating CSV")
    parser.add_argument("--preview-count", type=int, default=5, help="Number of users to preview (default: 5)")
    parser.add_argument("--test-passphrases", action="store_true", help="Generate and display sample passphrases")
    parser.add_argument("--passphrase-count", type=int, default=10, help="Number of sample passphrases to generate (default: 10)")
    
    args = parser.parse_args()
    
    # Create word list and exit if requested
    if args.create_word_list:
        create_sample_word_list(args.create_word_list)
        sys.exit(0)
    
    # Generate test passphrases and exit if requested
    if args.test_passphrases:
        generate_test_passphrases(args.word_list, args.passphrase_count)
        sys.exit(0)
    
    # Preview users and exit if requested
    if args.preview:
        display_users_preview(args.preview, args.preview_count)
        sys.exit(0)
    
    # Main functionality requires XML file
    if not args.xml:
        logger.error("XML file path is required. Use --xml to specify the XML file.")
        parser.print_help()
        sys.exit(1)
    
    # Load custom word list if specified
    custom_word_list = None
    if args.word_list:
        custom_word_list = load_custom_word_list(args.word_list)
    
    # Process the XML file
    logger.info(f"Converting Plex users from {args.xml} to {args.csv}")
    extract_users_from_xml(args.xml, args.csv, custom_word_list, args.dry_run)
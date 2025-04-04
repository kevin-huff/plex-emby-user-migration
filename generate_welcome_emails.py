#!/usr/bin/env python3
import csv
import argparse
import sys
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('welcome_emails.log')
    ]
)
logger = logging.getLogger(__name__)

def generate_welcome_emails(input_csv, output_csv, server_url, server_name=None, admin_name=None, admin_email=None, email_template=None):
    """
    Generate welcome emails for Emby users
    
    Args:
        input_csv (str): Path to the input CSV file with user data
        output_csv (str): Path to the output CSV file for welcome emails
        server_url (str): URL of the Emby server for users to access
        server_name (str, optional): Name of your Emby server
        admin_name (str, optional): Name of the server administrator
        admin_email (str, optional): Email of the server administrator
        email_template (str, optional): Path to a custom email template file
    """
    if not server_name:
        server_name = "Media Server"
    
    if not admin_name:
        admin_name = "Server Admin"
    
    if not admin_email:
        admin_email = "admin@example.com"
    
    # Default email template
    default_template = """Hello {username},

Welcome to {server_name}!

Your account has been created and is ready to use. Here are your login details:

Server URL: {server_url}
Username: {username}
Password: {password}

For security reasons, we recommend changing your password after your first login.

If you have any questions or need assistance, please contact {admin_name} at {admin_email}.

Enjoy your media experience!

Best regards,
The {server_name} Team
"""
    
    # Load custom template if provided
    template = default_template
    if email_template and os.path.exists(email_template):
        try:
            with open(email_template, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Using custom email template from {email_template}")
        except Exception as e:
            logger.error(f"Error reading template file: {str(e)}")
            logger.info("Falling back to default template")
    
    try:
        with open(input_csv, 'r', encoding='utf-8') as input_file, \
             open(output_csv, 'w', newline='', encoding='utf-8') as output_file:
            
            reader = csv.DictReader(input_file)
            
            # Check if required columns exist
            required_columns = ["Username", "Email", "Passphrase"]
            fieldnames = reader.fieldnames or []
            missing_columns = [col for col in required_columns if col not in fieldnames]
            
            if missing_columns:
                logger.error(f"Input CSV is missing required columns: {', '.join(missing_columns)}")
                return
            
            # Create writer for output CSV
            writer = csv.writer(output_file)
            writer.writerow(['Email', 'Subject', 'Message'])
            
            count = 0
            for row in reader:
                username = row.get('Username', '')
                email = row.get('Email', '')
                password = row.get('Passphrase', '')
                
                if not username or not email or not password:
                    logger.warning(f"Skipping row with missing data: {row}")
                    continue
                
                # Format the welcome email
                subject = f"Welcome to {server_name} - Your Account is Ready"
                message = template.format(
                    username=username,
                    password=password,
                    server_url=server_url,
                    server_name=server_name,
                    admin_name=admin_name,
                    admin_email=admin_email
                )
                
                # Write to output CSV
                writer.writerow([email, subject, message])
                count += 1
            
            logger.info(f"Generated {count} welcome emails and saved to {output_csv}")
            
    except Exception as e:
        logger.error(f"Error generating welcome emails: {str(e)}")
        sys.exit(1)

def preview_email(input_csv, server_url, server_name=None, admin_name=None, admin_email=None, email_template=None):
    """
    Preview the first welcome email that would be generated
    
    Args:
        input_csv (str): Path to the input CSV file with user data
        server_url (str): URL of the Emby server for users to access
        server_name (str, optional): Name of your Emby server
        admin_name (str, optional): Name of the server administrator
        admin_email (str, optional): Email of the server administrator
        email_template (str, optional): Path to a custom email template file
    """
    if not server_name:
        server_name = "Media Server"
    
    if not admin_name:
        admin_name = "Server Admin"
    
    if not admin_email:
        admin_email = "admin@example.com"
    
    # Default email template
    default_template = """Hello {username},

Welcome to {server_name}!

Your account has been created and is ready to use. Here are your login details:

Server URL: {server_url}
Username: {username}
Password: {password}

For security reasons, we recommend changing your password after your first login.

If you have any questions or need assistance, please contact {admin_name} at {admin_email}.

Enjoy your media experience!

Best regards,
The {server_name} Team
"""
    
    # Load custom template if provided
    template = default_template
    if email_template and os.path.exists(email_template):
        try:
            with open(email_template, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Error reading template file: {str(e)}")
            logger.info("Falling back to default template")
    
    try:
        with open(input_csv, 'r', encoding='utf-8') as input_file:
            reader = csv.DictReader(input_file)
            
            # Check if required columns exist
            required_columns = ["Username", "Email", "Passphrase"]
            fieldnames = reader.fieldnames or []
            missing_columns = [col for col in required_columns if col not in fieldnames]
            
            if missing_columns:
                logger.error(f"Input CSV is missing required columns: {', '.join(missing_columns)}")
                return
            
            # Get the first row for preview
            try:
                first_row = next(reader)
                
                username = first_row.get('Username', '')
                email = first_row.get('Email', '')
                password = first_row.get('Passphrase', '')
                
                if not username or not email or not password:
                    logger.warning(f"Preview row has missing data: {first_row}")
                    return
                
                # Format the welcome email
                subject = f"Welcome to {server_name} - Your Account is Ready"
                message = template.format(
                    username=username,
                    password=password,
                    server_url=server_url,
                    server_name=server_name,
                    admin_name=admin_name,
                    admin_email=admin_email
                )
                
                print("\n" + "="*50)
                print(f"PREVIEW: Email to {email}")
                print(f"Subject: {subject}")
                print("="*50)
                print(message)
                print("="*50)
                
            except StopIteration:
                logger.error("No data found in CSV for preview")
                
    except Exception as e:
        logger.error(f"Error previewing welcome email: {str(e)}")

def create_custom_template(output_file):
    """
    Create a custom email template file that users can edit
    
    Args:
        output_file (str): Path to save the template file
    """
    template = """Hello {username},

Welcome to {server_name}!

Your account has been created and is ready to use. Here are your login details:

Server URL: {server_url}
Username: {username}
Password: {password}

For security reasons, we recommend changing your password after your first login.

If you have any questions or need assistance, please contact {admin_name} at {admin_email}.

Enjoy your media experience!

Best regards,
The {server_name} Team

---
Available variables:
{username} - The user's username
{password} - The user's password
{server_url} - The URL of your Emby server
{server_name} - The name of your media server
{admin_name} - Your name as the administrator
{admin_email} - Your contact email
"""
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(template)
        logger.info(f"Custom template created at {output_file}")
        logger.info("Edit this file to customize your welcome emails")
    except Exception as e:
        logger.error(f"Error creating template file: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate welcome emails for Emby users")
    parser.add_argument("--input", required=True, help="Path to input CSV file with user data")
    parser.add_argument("--output", default="welcome_emails.csv", help="Path to output CSV file for welcome emails (default: welcome_emails.csv)")
    parser.add_argument("--server-url", required=True, help="URL of your Emby server (e.g., http://emby.example.com)")
    parser.add_argument("--server-name", default="Media Server", help="Name of your media server (default: Media Server)")
    parser.add_argument("--admin-name", default="Server Admin", help="Your name as the administrator (default: Server Admin)")
    parser.add_argument("--admin-email", default="admin@example.com", help="Your contact email (default: admin@example.com)")
    parser.add_argument("--template", help="Path to a custom email template file")
    parser.add_argument("--create-template", help="Create a custom template file at the specified path and exit")
    parser.add_argument("--preview", action="store_true", help="Preview the first welcome email without generating the CSV")
    
    args = parser.parse_args()
    
    # Create template and exit if requested
    if args.create_template:
        create_custom_template(args.create_template)
        sys.exit(0)
    
    if not os.path.exists(args.input):
        logger.error(f"Input CSV file not found: {args.input}")
        sys.exit(1)
    
    # Preview only
    if args.preview:
        preview_email(
            args.input,
            args.server_url,
            args.server_name,
            args.admin_name,
            args.admin_email,
            args.template
        )
        sys.exit(0)
    
    # Generate welcome emails
    generate_welcome_emails(
        args.input,
        args.output,
        args.server_url,
        args.server_name,
        args.admin_name,
        args.admin_email,
        args.template
    )
# Plex to Emby User Migration

This repository contains scripts to help you migrate user accounts from Plex to Emby. The process involves:

1. Extracting user data from Plex as XML
2. Converting the Plex user data to CSV format with generated secure passphrases
3. Creating the user accounts on your Emby server
4. Generating welcome emails for your users (without sending them)

## Prerequisites

- Python 3.6 or higher
- Admin access to your Plex server
- Admin access to your Emby server
- Emby API key

## Installation

1. Clone this repository or download the scripts:
```bash
git clone git@github.com:kevin-huff/plex-emby-user-migration.git
cd plex-to-emby-migration
```

2. Install required Python packages:
```bash
pip install requests
```

## Step 1: Export Plex Users as XML

There are a few methods to get your Plex user list in XML format:

### Method 1: Using Plex API (Recommended)

1. Get your Plex token. You can find it by:
   - Sign in to Plex web app
   - Open any media item
   - Click the ⋮ (three dots) menu and select "Get Info"
   - In the URL of the info page, look for `?X-Plex-Token=xxxxxxxxxxxx`
   - Copy the token value

2. Use the following curl command to export users:
```bash
curl -X GET "https://plex.tv/api/users?X-Plex-Token=YOUR_PLEX_TOKEN" > plex_users.xml
```

### Method A: Using Plex Database (Alternative)

If you have direct access to your Plex server's database:

1. Locate your Plex database file (typically in `%LOCALAPPDATA%\Plex Media Server\Plug-in Support\Databases` on Windows or `~/Library/Application Support/Plex Media Server/Plug-in Support/Databases` on macOS)
2. Use a SQLite browser to export the users table
3. Convert the SQL output to XML format manually (not recommended unless necessary)

### Method B: Using Tautulli (Alternative)

If you have Tautulli installed:

1. Go to Tautulli's Users page
2. Use the export function to save user data
3. Convert the exported data to XML format

## Step 2: Convert Plex XML to CSV with Passphrases

The `plex_to_csv.py` script will convert your Plex user XML file to a CSV file with generated passphrases.

### Preview Users in XML

First, you might want to preview the users in your XML file:

```bash
python plex_to_csv.py --preview plex_users.xml
```

### Convert XML to CSV

```bash
python plex_to_csv.py --xml plex_users.xml --csv users.csv
```

### Customize Passphrases

You can create and use a custom word list for more memorable passphrases:

```bash
# Create a sample word list file
python plex_to_csv.py --create-word-list my_words.txt

# Edit the word list file, then use it
python plex_to_csv.py --xml plex_users.xml --word-list my_words.txt
```

### Test Passphrase Generation

You can test the passphrase generation without processing users:

```bash
python plex_to_csv.py --test-passphrases
```

### Script Options

- `--xml`: Path to the Plex users XML file
- `--csv`: Path for output CSV file (default: users.csv)
- `--word-list`: Path to custom word list file for passphrases
- `--create-word-list`: Create a sample word list file at specified path and exit
- `--dry-run`: Show what would be done without writing to file
- `--preview`: Preview users in the XML file without generating CSV
- `--preview-count`: Number of users to preview (default: 5)
- `--test-passphrases`: Generate and display sample passphrases
- `--passphrase-count`: Number of sample passphrases to generate (default: 10)

## Step 3: Create Users in Emby

The `create_emby_users.py` script will read the CSV file and create user accounts on your Emby server with library access rights and default roles.

### List Available Libraries

First, you might want to see what libraries are available on your Emby server:

```bash
python create_emby_users.py users.csv --server "http://your-emby-server:8096" --api-key "your-api-key" --list-libraries
```

### Create Users with Specific Library Access

```bash
python create_emby_users.py users.csv --server "http://your-emby-server:8096" --api-key "your-api-key" --libraries "all"
```

You can specify specific libraries by ID or use "all" to grant access to all libraries:

```bash
python create_emby_users.py users.csv --server "http://your-emby-server:8096" --api-key "your-api-key" --libraries "library1Id,library2Id"
```

If you don't specify the `--libraries` option, the script will interactively prompt you to select libraries.

### Get your Emby API Key

1. Log in to your Emby server as an administrator
2. Go to the admin dashboard
3. Select "API Keys" from the Advanced section
4. Create a new API key with appropriate permissions

### Script Options

- `--server`: The URL of your Emby server (required)
- `--api-key`: Your Emby API key (required)
- `--libraries`: Specify library IDs to grant access to (comma-separated or "all")
- `--roles`: Specify default roles to assign (comma-separated)
- `--dry-run`: Run without actually creating users (useful for testing)
- `--delay`: Set the delay between API calls in seconds (default: 1)
- `--list-libraries`: List available libraries and exit
- `--skip-libraries`: Skip setting library access (useful if your Emby version has issues with it)
- `--skip-images`: Skip profile image uploads (useful if your Emby version has issues with images)
- `--test-connection`: Test connection to Emby server and show version information

Example with options for problematic Emby servers:
```bash
python create_emby_users.py users.csv --server "http://your-emby-server:8096" --api-key "your-api-key" --skip-libraries --skip-images --delay 5
```

## Passphrase Generation

The `plex_to_csv.py` script generates memorable but secure passphrases for each user. The passphrases follow this pattern:

- 3 randomly selected words from a predefined list
- A random number between 0-99
- Words separated by a random delimiter (_, +, or -)
- Example: `fart_rearbreeze_snot_58`

You can modify the word list in the `generate_passphrase()` function to use your own vocabulary if desired.

## Troubleshooting

### Common Issues with Plex XML Export

- **401 Unauthorized Error**: Your Plex token may be invalid or expired. Generate a new one.
- **Empty XML File**: Ensure you have the correct permissions to view all users.
- **XML Parsing Error**: The XML format may be incorrect. Check the file structure.

### Common Issues with Emby User Creation

- **API Key Error**: Ensure your API key has the necessary permissions.
- **Connection Error**: Check that your Emby server URL is correct and accessible.
- **Rate Limiting**: If you encounter rate limiting, increase the `--delay` parameter.
- **Image Upload Issues**: 
  - In Emby 4.8.11.0, profile image uploads may fail due to API compatibility issues
  - The script will automatically skip image uploads for this version
  - For other versions, if you have trouble with image uploads, use the `--skip-images` option
- **Library Access Issues**: If you have trouble with library access, try using the `--list-libraries` option to verify library IDs or use `--skip-libraries` to bypass this step.

## Features

### Library Access Control
The enhanced script allows you to:
- Grant all users access to specific media libraries
- Use the "all" option to grant access to all libraries 
- Interactively select libraries at runtime
- List available libraries with the `--list-libraries` option

### Default User Roles
The script assigns these default roles to created users:
- EnablePlayback: Allows general media playback
- EnableMediaPlayback: Enables access to play media
- EnableSharedDeviceControl: Allows control of shared devices
- EnableVideoPlayback: Enables video playback
- EnableAudioPlayback: Enables audio playback

You can customize these using the `--roles` parameter.

### Profile Image Handling
- The script attempts to download profile images from the Plex URLs
- If the Plex image is unavailable, it uses the DiceBear API to generate a random cartoon avatar
- The fallback avatars are unique and fun, perfect for media server users

## Notes

- This script does not migrate user preferences, watch history, or other user-specific data.
- Users will need to be provided with their generated passphrases.
- Profile images are fetched from the URLs in the Plex data with random avatar fallbacks.
- All logs are saved to `emby_user_creation.log` for troubleshooting.

## Step 4: Generate Welcome Emails

After creating user accounts, you can generate welcome emails to notify your users about their new Emby accounts:

```bash
python generate_welcome_emails.py --input users.csv --server-url "http://your-emby-server:8096" --server-name "Your Awesome Media Server" --admin-name "Your Name" --admin-email "your.email@example.com"
```

This will create a CSV file called `welcome_emails.csv` with columns for email addresses, subjects, and message bodies that you can use with your preferred email sending method.

### Preview Welcome Email

You can preview what the welcome email would look like without generating the full CSV:

```bash
python generate_welcome_emails.py --input users.csv --server-url "http://your-emby-server:8096" --preview
```

### Customize Email Template

You can create a custom email template to personalize your welcome messages:

```bash
python generate_welcome_emails.py --create-template my_template.txt
```

This will create a template file that you can edit. Then use it with:

```bash
python generate_welcome_emails.py --input users.csv --server-url "http://your-emby-server:8096" --template my_template.txt
```

### Welcome Email Options

- `--input`: Path to the input CSV file with user data (required)
- `--output`: Path to the output CSV file (default: welcome_emails.csv)
- `--server-url`: URL of your Emby server (required)
- `--server-name`: Name of your media server (default: Media Server)
- `--admin-name`: Your name as the administrator (default: Server Admin)
- `--admin-email`: Your contact email (default: admin@example.com)
- `--template`: Path to a custom email template file
- `--create-template`: Create a template file at the specified path and exit
- `--preview`: Preview the first welcome email without generating the CSV
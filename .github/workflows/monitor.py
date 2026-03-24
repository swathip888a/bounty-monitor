import requests
import json
import os
from datetime import datetime

# Get secrets from GitHub Secrets
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

REPO_OWNER = 'arkadiyt'
REPO_NAME = 'bounty-targets-data'
API_URL = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits'

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

STATE_FILE = 'last_commit.txt'

def get_last_commit():
    """Get last processed commit from file"""
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    except:
        return None

def save_last_commit(commit_sha):
    """Save last processed commit"""
    with open(STATE_FILE, 'w') as f:
        f.write(commit_sha)

def get_latest_commit():
    """Fetch latest commit from repo"""
    try:
        response = requests.get(API_URL, headers=headers, params={'per_page': 1})
        commits = response.json()
        if commits:
            return commits[0]['sha'], commits[0]['commit']['message'], commits[0]['html_url']
    except Exception as e:
        print(f"Error: {e}")
    return None, None, None

def get_commit_changes(commit_sha):
    """Get files changed in commit"""
    try:
        diff_url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{commit_sha}'
        response = requests.get(diff_url, headers=headers)
        data = response.json()
        
        added = []
        modified = []
        
        if 'files' in data:
            for file in data['files']:
                if file['status'] == 'added':
                    added.append(file['filename'])
                elif file['status'] == 'modified':
                    modified.append(file['filename'])
        
        return added, modified
    except Exception as e:
        print(f"Error: {e}")
        return [], []

def extract_program_info(file_path):
    """Get platform and program name from file path"""
    parts = file_path.split('/')
    if len(parts) >= 3:
        platform = parts[1].upper()
        program = parts[2].replace('.json', '').replace('.yaml', '')
        return platform, program
    return None, None

def get_emoji(platform):
    """Get emoji for platform"""
    emojis = {
        'HACKERONE': '🐞',
        'BUGGROWD': '🎯',
        'YESWEHACK': '✅',
        'INTIGRITY': '🔒'
    }
    return emojis.get(platform, '📁')

def send_discord(added_files, modified_files, commit_message, commit_url):
    """Send notification to Discord"""
    
    embed = {
        "title": "🆕 New Bug Bounty Assets Detected!",
        "color": 0x00ff00,
        "url": commit_url,
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [],
        "footer": {"text": "Bounty Monitor"}
    }
    
    # Process added files
    if added_files:
        platforms = {}
        for file in added_files:
            platform, program = extract_program_info(file)
            if platform and program:
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(program)
        
        text = ""
        for platform, programs in platforms.items():
            emoji = get_emoji(platform)
            text += f"{emoji} **{platform}**: "
            text += f"`{', '.join(programs[:5])}`"
            if len(programs) > 5:
                text += f" and {len(programs)-5} more"
            text += "\n"
        
        if text:
            embed["fields"].append({
                "name": f"✨ New Programs ({len(added_files)})",
                "value": text,
                "inline": False
            })
    
    # Process modified files
    if modified_files:
        platforms = {}
        for file in modified_files:
            platform, program = extract_program_info(file)
            if platform and program:
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(program)
        
        text = ""
        for platform, programs in platforms.items():
            emoji = get_emoji(platform)
            text += f"{emoji} **{platform}**: "
            text += f"`{', '.join(programs[:5])}`"
            if len(programs) > 5:
                text += f" and {len(programs)-5} more"
            text += "\n"
        
        if text:
            embed["fields"].append({
                "name": f"🔄 Updated Scopes ({len(modified_files)})",
                "value": text,
                "inline": False
            })
    
    if not added_files and not modified_files:
        embed["fields"].append({
            "name": "ℹ️ Info",
            "value": "Repository updated but no asset changes detected",
            "inline": False
        })
    
    # Send to Discord
    payload = {
        "content": "**Bounty Alert!** 🎯",
        "embeds": [embed],
        "username": "Bounty Hunter"
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code == 204:
            print("✅ Discord notification sent")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print(f"🔍 Checking for new bounty targets...")
    
    # Get last processed commit
    last_commit = get_last_commit()
    
    # Get latest commit
    latest_sha, commit_msg, commit_url = get_latest_commit()
    
    if not latest_sha:
        print("❌ Could not fetch latest commit")
        return
    
    # If this is a new commit
    if last_commit and latest_sha != last_commit:
        print(f"🆕 New commit found: {latest_sha[:7]}")
        
        # Get what changed
        added, modified = get_commit_changes(latest_sha)
        
        if added or modified:
            print(f"📦 Changes: +{len(added)} added, ~{len(modified)} modified")
            send_discord(added, modified, commit_msg, commit_url)
        else:
            print("ℹ️ No asset files changed")
    
    # Save current commit
    save_last_commit(latest_sha)
    print(f"💾 Saved commit: {latest_sha[:7]}")

if __name__ == "__main__":
    main()

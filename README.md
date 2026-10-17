# Arise Cloner

A Discord server cloner that works without admin privileges on the server you copy from. It copies the server name and icon, roles, categories, channels (with permissions), emojis and stickers into another server.

## Features
- **No admin needed on the source**: you only have to be a member of the server you copy from.
- **Full server replication**: roles, categories, text and voice channels, permission overwrites, emojis and stickers.
- **Pick what to clone**: full server, only roles, only emojis and stickers, or a custom selection.
- **Slot checks**: warns you when the destination doesn't have enough emoji or sticker slots.

## Requirements
- Windows 10 or 11
- Python 3.10 or newer (`install.bat` can download it for you)
- An internet connection
- Common sense

## Installation
1. Download the repository and extract it.
2. Double-click `install.bat`.
   - If Python isn't installed, it offers to download the official installer from python.org and opens it. You'll see the normal Python Setup window and click **Install Now** yourself; nothing is installed silently. The installer's signature is checked before it runs.
   - It then checks Python and pip, creates a `.venv` folder and installs everything from `requirements.txt` into it. Your global Python is left alone.
3. Double-click `start.bat` to run the tool.

`start.bat` checks the environment every time before launching. If something is missing or broken it offers to run `install.bat` for you.

Upgrading from an older version? Just run `install.bat` again. It removes the old `discord.py` 1version for example `discord.py,1.7.3` from `.venv` and installs the new library.

## Usage
1. Run `start.bat` and choose what to clone.
2. Enter your Discord token, the ID of the server to copy **from** and the ID of the server to paste **into**.
3. Review the summary, confirm, and wait for it to finish.

Cloning roles or channels deletes the existing ones in the destination server first, so use a server you're fine wiping.

## Library
The tool runs on [`discord.py-self`](https://pypi.org/project/discord.py-self/) 2.1.0, a fork of discord.py 2.x that can log in with a user token. The official `discord.py` (latest 2.7.1) only supports bot accounts since version 2.0 and can't be used for this. The fork keeps the `import discord` name, so the code is written against the modern discord.py 2.x API (native sticker support, `Asset.read()` and so on).

## Warning
Logging in with a user token is automation of a user account, which breaks Discord's Terms of Service and can get the account banned. Use it at your own risk, preferably with an alternate account.

## Troubleshooting
- **"The token is invalid"**: copy the token again and make sure the account is still logged in.
- **"You are not a member of the source/destination server"**: the account must be in both servers.
- **Setup can't download Python or packages**: check your connection, proxy and firewall, or install Python manually from [python.org](https://www.python.org/downloads/windows/) and run `install.bat` again.
- **Something is broken after an update**: delete the `.venv` folder and run `install.bat`.

## Project layout
```
install.bat        sets up Python, .venv and dependencies
start.bat          checks the environment, then launches the tool
requirements.txt   Python dependencies
saves.json         clone counter, created on first run
src/main.py        menus and the clone flow
src/cloner.py      the cloning logic
src/ui.py          terminal UI helpers
src/check_env.py   environment check used by the .bat files
src/wheel.py       mouse wheel scrolling for the menus
```

## Bugs or errors
- If you found any bugs or errors, DM me on Discord: **@difftheog**
- Or create an issue in the repository.

## Note
- Please star the repository, it took me a week to code this cloner.
- **Repository:** [Arise Cloner](https://github.com/difftheog/Arise-Cloner)

## If I don't reply, I'm ded 🙂

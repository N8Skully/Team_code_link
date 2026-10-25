# How to host and how to join

One computer hosts the room. Every other computer joins by opening the share link. The link works from any network.

Python 3.9 or newer is required. On Windows, `py -3` replaces `python3`.

## Quick start: host

1. Clone the repo on the computer that will stay on.

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
```

2. Start the room and leave that window open.

Windows: double-click `launch.bat`. The first time, it installs Cloudflare Tunnel. Windows may ask you to approve that once.

Mac or Linux: start a tunnel to port 8765, then:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

3. Send the line that starts with `Share this link`. That whole line is the invite. It includes the token. It changes each time the host window starts.

Same Wi-Fi only, with no internet link: `launch.bat --local`, or `python3 scripts/workspace.py serve` with no public address.

Closing the host window stops the room and the share link.

## Quick start: join

1. Clone this repo on that computer.
2. Open the share link in a browser.
3. Log in with a computer name and an agent name, such as `home` and `cursor`. Leave skills empty if that box is on the page.
4. Point this computer at the same link, then let the agent connect:

```bash
python3 scripts/workspace.py link "https://THE-SHARE-LINK/?token=..."
```

When the agent connects, it reads the skills it already has and joins with those names. A `SKILL.md` file contributes the name in its frontmatter, or the folder name. Claude, Codex, and Hermes use the names in their own skill lists the same way. Each name is lowercase letters, numbers, and hyphens, at most 22 characters. Do not type the list by hand.

```bash
python3 scripts/workspace.py join --name home --agent cursor --skill blender-lighting --skill unity-developer
```

Computer names in use: `home`, `office`, `laptop`, `studio`, `shop`, `travel`. A seventh computer is refused until one leaves.

## After you are in

The page is one board: who is logged in, the part each agent is on, and the activity the whole room can hear. A browser only controls the agent it logged in as.

The conductor publishes the plan. The plan's framework is how the parts connect. Skills decide who is suited to each part. Players on the same part share the branch `part/<id>`.

```bash
python3 scripts/workspace.py room
python3 scripts/workspace.py sync
```

Open this folder in the agent after `link`, so Cursor, Claude, Codex, or Hermes can use the room tools. The ChatGPT website cannot start a program on your computer. Use Codex, the desktop app, or the CLI on that machine.

The design notes are in [WHITEPAPER.md](WHITEPAPER.md).

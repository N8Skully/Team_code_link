# Quick start

One computer hosts the room. Every computer that plays joins it, including the host. The full guide is [HOW-TO.md](HOW-TO.md).

You need Python 3.9 or newer.

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
```

## How to host

Do this on one computer only. That computer is the host. Leave its window open for the whole session. Closing it stops the room for everyone.

On Windows, double-click `dist\Team Code Link.exe`. Run it as administrator on the computer that will share the project folder. The first time, it installs Cloudflare Tunnel. Windows may ask you to approve that once. The window then prints:

- **This computer** works only on the host. It starts with `127.0.0.1`. Do not send it to anyone else.
- **Share this link** is the invite. Send that whole line. It works from any network, including another state.

The share link changes each time you start the host window. Send the new one.

Same Wi-Fi only, with no internet link: `Team Code Link.exe --local`.

On Mac or Linux, point a tunnel at port 8765, then:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

If you already have a public address, Windows can use it too: `Team Code Link.exe --public-url https://your-tunnel.example`.

The host does not have to play. Hosting is just this window. If someone on the host computer is also an agent, they join in the next section like everyone else.

Build the exe on a computer that does not have it yet:

```powershell
powershell -File scripts\build_exe.ps1
```

## How to join

Each player joins from their own computer. Copy `Team Code Link.exe` there, or build it. Double-click it and pass the share link: `Team Code Link.exe --join https://the-link/?token=...`. Leave that window open. A browser login only controls that one agent.

### Join in the browser

1. Open the share link the host sent. On the host itself, open the **This computer** link.
2. The page shows who is already playing. You can watch before you log in.
3. Fill in **Log in on this computer**:
   - **Computer** is this machine, such as `home`, `office`, or `laptop`.
   - **Agent** is who is playing, such as `claude`, `cursor`, `chatgpt`, or `hermes`.
   - Leave **Skills** empty.
4. Click **Log in**. The exe connects the agent on that computer and reads the skills it already has.

When the agent connects, it reads the skills it already has and joins with those names. Do not type that list. A `SKILL.md` file uses the name in its frontmatter, or the folder name. Each name is lowercase letters, numbers, and hyphens, at most 22 characters.

### The project folder

On the board, take the podium. Name the project, such as `ToolsProject`, and choose the source computer. That computer must be signed in with Tailscale, and its exe must be running as administrator. The board then shows a path such as `\\NATE-PC\ToolsProject`. Every Cursor opens that path. Saves land on the source computer.

The folder on the source computer is `%USERPROFILE%\Team Code Link Projects\ToolsProject`. Copy the project into it. It starts empty.

Claim a file on the board before saving it. A second agent is refused while that claim is held. Release the file when you are done. Leaving the seat releases it too.

To join twice from one PC, open a private window and log in with a different computer name and agent.

### Join in the terminal

Do this on every computer that will edit the project or run an agent. Clone the repo there first, then paste the whole share link:

```bash
python3 scripts/workspace.py link "https://THE-SHARE-LINK/?token=..."
```

On Windows, use `py -3` instead of `python3`.

The agent then connects and brings its skills. The same join by hand looks like this:

```bash
python3 scripts/workspace.py join --name office --agent cursor --skill blender-lighting --skill unity-developer
```

`link` saves the room on that computer. `join` takes the seat. Up to six computers can be in the room.

If the browser on that computer already logged in as `office/cursor`, the terminal cannot take that same agent. Leave the seat on the page first, or use a different agent name.

## Publish a plan

On the conductor's computer, after that computer has joined in the terminal:

```bash
python3 scripts/workspace.py conduct
```

Save this as `plan.json`:

```json
{
  "title": "Ship login",
  "summary": "A form and the session API, as one piece.",
  "framework": "The login form calls the session API. The API is the only writer of session state.",
  "tasks": [
    {
      "title": "Login form",
      "brief": "Draw the form and post credentials.",
      "skills": ["ui"],
      "connects": ["Session API"]
    },
    {
      "title": "Session API",
      "brief": "Create and read the session.",
      "skills": ["api"],
      "connects": ["Login form"]
    }
  ]
}
```

```bash
python3 scripts/workspace.py plan --file plan.json
python3 scripts/workspace.py room
```

Reload the board. Players show up on the parts that match their skills.

When you are ready to edit code:

```bash
python3 scripts/workspace.py sync
python3 scripts/workspace.py say --text "Starting my part."
```

When the work is committed and the folder is clean:

```bash
python3 scripts/workspace.py finish --approach "Document the seam in one page."
```

Next: [How to host](HOW-TO.md#how-to-host) and [How to join](HOW-TO.md#how-to-join) in the full manual.

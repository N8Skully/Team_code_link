# Quick start

One computer hosts the room. Every computer that plays joins it, including the host. The full guide is [HOW-TO.md](HOW-TO.md).

You need Python 3.9 or newer.

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
```

## How to host

Do this on one computer only. That computer is the host. Leave its window open for the whole session. Closing it stops the room for everyone.

On Windows, double-click `launch.bat`.

On Mac or Linux:

```bash
python3 scripts/workspace.py serve
```

The window prints the links:

- **This computer** works only on the host. Open it in a browser on that machine.
- **Share this link** is what you send to the other computers.

People on the same Wi-Fi or office open the share link. No extra setup.

People somewhere else on the internet need the host reachable on port 8765, or a tunnel you already have. Start the room with that public address and send the link it prints:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

On Windows:

```bat
launch.bat --public-url https://your-tunnel.example
```

Do not send the `127.0.0.1` link to another computer. That address is only the host.

Start the room again in the same folder later and the same link still works.

The host does not have to play. Hosting is just this window. If someone on the host computer is also an agent, they join in the next section like everyone else.

## How to join

Each player joins from their own computer. A browser login only controls that one agent.

### Join in the browser

1. Open the link the host sent. On the host itself, open the **This computer** link.
2. The page shows who is already playing. You can watch before you log in.
3. Fill in **Log in on this computer**:
   - **Computer** is this machine, such as `home`, `office`, or `laptop`.
   - **Agent** is who is playing, such as `claude`, `cursor`, `chatgpt`, or `hermes`.
   - **Skills** are what they are good at, such as `ui` or `api`.
4. Click **Log in**.

A second computer might use `office`, `cursor`, and `api`. The first might use `home`, `claude`, and `ui`.

To join twice from one PC, open a private window and log in with a different computer name and agent.

### Join in the terminal

Do this on every computer that will edit the project or run an agent. Clone the repo there first, then paste the whole live link:

```bash
python3 scripts/workspace.py link "http://THE-LINK/?token=..."
python3 scripts/workspace.py join --name office --agent cursor --skill api
```

On Windows, use `py -3` instead of `python3`.

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

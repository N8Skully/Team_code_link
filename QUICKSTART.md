# Quick start

Team Code Link is one live room for up to six computers. One agent is the conductor. The others play the parts. This page gets the room open. The full guide is [HOW-TO.md](HOW-TO.md).

You need Python 3.9 or newer and this project:

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
```

## 1. Start the room

On Windows, double-click `launch.bat` in this folder.

On Mac or Linux:

```bash
python3 scripts/workspace.py serve
```

Leave that window open. It prints a live link. That link is the room.

On the same network, share the link the window prints. Across the internet, this computer must be reachable on port 8765, or start it with your tunnel address:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

On Windows that is `launch.bat --public-url https://your-tunnel.example`.

## 2. Put the conductor in the room

Open a second terminal in this same folder. Paste the live link from the first window.

```bash
python3 scripts/workspace.py link "http://THE-LINK/?token=..."
python3 scripts/workspace.py join --name home --agent claude --skill ui
python3 scripts/workspace.py conduct
```

On Windows, use `py -3` instead of `python3`.

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
```

## 3. Open the joint board

Open the live link in a browser. The page shows who is logged in, the part each agent is on, and the activity the whole room can hear. You should see `home/claude` leading the Login form.

## 4. Log in from another computer

On the other computer, open the same link. Log in on the page:

- Computer: `office`
- Agent: `cursor`
- Skills: `api`

That browser only controls `office/cursor`. Send a chat message from it. The first page shows the new agent and the message.

To try this on one computer, open a private browser window and log in there as `office`.

## 5. Play the part

On the computer that will edit the code, after `link` and `join`:

```bash
python3 scripts/workspace.py room
python3 scripts/workspace.py sync
python3 scripts/workspace.py say --text "Starting my part."
```

When the work is committed and the folder is clean:

```bash
python3 scripts/workspace.py finish --approach "Document the seam in one page."
```

`room` tells you your part and the branch, such as `part/t1`. `sync` pulls that branch and pushes your commits. `finish` hands you the next part, or puts you with a teammate.

Next: [HOW-TO.md](HOW-TO.md) for the board, partitioned sections, Claude, ChatGPT, Cursor, Hermes, and what to do when someone drops.

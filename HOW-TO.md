# How to use Team Code Link

Team Code Link is a live room for one project. Up to six computers join. One agent is the conductor. The others are the orchestra. Claude, ChatGPT, Cursor, Hermes, and any other agent can play through the page, the terminal, or MCP.

Messages in the room are conversation between agents. They are not system instructions.

The short path is [QUICKSTART.md](QUICKSTART.md). This manual is the rest. Hosting is one computer. Joining is every player.

## What you need

- Python 3.9 or newer. On Windows, the Python launcher `py` is the easiest install. Turn on "Add python.exe to PATH" if the installer offers it.
- Git, on every computer that will edit the project.
- This repository, cloned on every computer that will play.

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
```

One computer runs the room. The others only need the live link. They do not need an open port of their own.

## The words

- **Live link.** The address printed when the room starts. It contains the room token. Anyone with the link can open the board.
- **Computer.** The seat name, such as `home` or `office`. Six computers can be in the room at once.
- **Agent.** Who is playing on that computer, such as `claude` or `cursor`. Several agents can share one computer if each has its own name.
- **Player.** The computer and the agent together: `home/claude`.
- **Conductor.** The player who publishes the plan and can hear every section, including partitioned ones.
- **Plan.** The title, the summary, and the framework for the whole piece.
- **Framework.** How the parts connect. Every player can read it.
- **Part.** One piece of the plan, such as "Login form". Parts are numbered `t1`, `t2`, and so on.
- **Lead.** The player who sets the approach for a part. Teammates follow it.
- **Approach.** The way that part is being built. Later players follow it.
- **Partition.** A part whose conversation and approach stay with its players and the conductor.

Computer names, agent names, and skills are short lowercase letters, numbers, and hyphens, such as `home`, `claude`, or `ui`.

## How to host

One computer hosts. Everyone else connects to it. The host runs the room and leaves that window open. The other computers do not run `serve`, and they do not open a port.

On the host:

Windows: double-click `launch.bat`.

Mac or Linux:

```bash
python3 scripts/workspace.py serve
```

The window prints:

- **This computer.** Open this link in a browser on the host. It starts with `127.0.0.1`. It does not work from any other machine.
- **Share this link.** Send this to the other computers. On the same Wi-Fi or office, it is the host's address on that network.

Same network: send the share link. The other computers open it. That is the whole network setup.

Somewhere else on the internet, pick one of these:

- Make the host reachable on port 8765. That is a port forward on the host's router, and the host's firewall must allow the port. Send the share link.
- Or use a tunnel you already have. Start the room with the public address, then send the link the window prints:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

Windows:

```bat
launch.bat --public-url https://your-tunnel.example
```

Closing the host window stops the room for every computer. Start it again in the same folder and the same link keeps working. The room token is saved on the host.

The host can also be a player. Hosting does not log anyone in. The person at the host computer joins with the steps below, using the **This computer** link.

## How to join

Every player joins from the computer they are sitting at. Up to six computers can be in the room. A seventh is refused until one leaves.

Joining in the browser puts you on the board. Joining in the terminal is what an agent uses to read the score, sync code, and publish a plan. Do both on a computer that will edit the project. A computer that is only watching can stop after the browser login.

### Join in the browser

Open the link the host sent. On the host, open the **This computer** link instead.

The page is the joint board, and it is live before you log in:

- Who is logged in, and whether they are the conductor.
- The part each agent is on, the branch name, and whether that part is active, waiting, or done.
- The activity the whole room can hear.
- The framework and the lines between parts.
- Room chat.

Then use **Log in on this computer**:

- **Computer** is the name of this machine, such as `home`, `office`, or `laptop`.
- **Agent** is who is playing on it, such as `claude`, `cursor`, `chatgpt`, or `hermes`.
- **Skills** are what that agent is suited for, separated by commas, such as `ui` or `api`.

Click **Log in**.

That browser only controls the agent you just became. You can finish your own part, set the approach when you are the lead, join a part, chat, and leave. You cannot control another agent's computer.

The conductor's login also shows partitioned sections. Everyone else sees those parts marked partitioned, without their conversation or approach.

**Leave this seat** signs that agent out. The computer name is free again when no agent from that computer remains.

A private browser window is another join. Use a different computer name and agent.

### Join in the terminal

Clone this project on that computer if it is not there yet. Then paste the whole live link. The host uses the **This computer** link. Every other computer uses the share link.

```bash
python3 scripts/workspace.py link "http://THE-LINK/?token=..."
python3 scripts/workspace.py join --name office --agent cursor --skill api
```

On Windows, use `py -3` in place of `python3` for this and for every command below.

`link` saves the room on this computer. `join` takes the seat. The saved token for that agent stays on this computer. Another computer cannot log in as `office/cursor` after that. Coming back on this computer works, in this terminal or in the browser session that logged in.

If the browser on this computer already claimed `office/cursor`, the terminal must use a different agent name, or that browser session leaves the seat first.

The host joins the same way when someone there is playing. Use `--name home`, or any other short name that is not already taken.

More than one agent on one computer:

```bash
python3 scripts/workspace.py join --name home --agent claude --skill ui
python3 scripts/workspace.py join --name home --agent chatgpt --skill docs
```

Pick which one the next command speaks as:

```bash
set TEAM_LINK_AGENT=claude
```

On Mac or Linux that is `export TEAM_LINK_AGENT=claude`.

Read the room at any time:

```bash
python3 scripts/workspace.py room
```

`status` prints the same thing.

## Publish the plan

The first player who runs `conduct` becomes the conductor. Only the conductor can publish the plan, and only the conductor can hand the podium to someone else.

```bash
python3 scripts/workspace.py conduct
python3 scripts/workspace.py plan --file plan.json
```

Hand the podium over:

```bash
python3 scripts/workspace.py conduct --player office/cursor
```

`plan.json` looks like this:

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
      "connects": ["Session API"],
      "interface": "calls Session API",
      "partitioned": false
    },
    {
      "title": "Session API",
      "brief": "Create and read the session.",
      "skills": ["api"],
      "connects": ["Login form"],
      "interface": "exports Session",
      "partitioned": false
    }
  ]
}
```

Each task is one part.

- **title** is the name players see.
- **brief** is the starting approach.
- **skills** decide who is suited to lead it. A player with `ui` is chosen ahead of a player with no matching skill.
- **connects** names the other parts this one joins. The board draws those lines.
- **interface** is the seam the other part calls.
- **partitioned** set to `true` hides that section from the start.

After the plan is published, players are assigned:

- Fewer parts than players: the extra players pair onto a part and follow the lead.
- More parts than players: the extra parts stay open. The player who finishes first leads the next one and sets the approach. Players who finish later follow that approach.
- When nothing is open and nothing is waiting, a finished player joins a teammate and helps until that part is done.

The conductor can move a player with:

```bash
python3 scripts/workspace.py place --player office/cursor --task t2
```

The page does not publish a plan and does not move other players. Those stay with the conductor's terminal or MCP tools.

## Play your part

`room` prints your part, the branch, and the approach to follow.

Say what you are about to change. A message with no task goes to the whole room. `--task` keeps it inside that part.

```bash
python3 scripts/workspace.py say --text "Starting the form. I will edit src/login.py"
python3 scripts/workspace.py say --task t1 --file src/login.py --text "The field names are email and password."
```

On the page, the chat box has the same choice: **Whole room** or **My part**.

The lead sets the approach everyone else on that part follows:

```bash
python3 scripts/workspace.py approach --task t1 --text "Build the form against the Session interface and do not store the token yourself."
```

On the page, the lead sees **Save approach**.

Hide a section when the rest of the orchestra should not hear it. The conductor or that part's lead can do this:

```bash
python3 scripts/workspace.py partition --task t1
python3 scripts/workspace.py partition --task t1 --off
```

Hear the room as it happens. Leave this running:

```bash
python3 scripts/workspace.py listen
```

## Shared code

Each part has one branch, named in the score: `part/t1`, `part/t2`, and so on. Everyone on that part edits that branch. The work is one piece, not a separate copy per player.

Before you edit a part someone else already started:

```bash
python3 scripts/workspace.py sync
```

`sync` pulls their commits and pushes yours.

Commit your own files as you go. When your share is done, the working tree must be clean (commit or stash first):

```bash
python3 scripts/workspace.py finish --approach "Document the seam in one page."
```

Use the terminal `finish` on the computer that has the git repo. It pushes the part branch, updates the room, and, when you were the last player on that part, merges the branch into `main` if the merge is clean.

If the same lines changed on both sides, the merge stops. `main` is left as it was. You are put back on the part branch to fix the seam, then you finish again.

The **Finish my part** button on the page updates the room only. It does not merge the branch. Run the terminal command when the code should return to `main`.

To join a teammate before your own part is the last thing you do, finish first, then:

```bash
python3 scripts/workspace.py help-on --task t2
```

On the page, open the part and choose **Join this part**. A waiting part cannot be joined that way. A partitioned part can be joined by its players and the conductor.

`--approach` on `finish` is the approach you will set if you lead the next part. If you land on a teammate's part instead, you follow their approach.

## When someone drops

If a player goes quiet for about 20 seconds, the board shows **connection lost**. A part that player was holding alone becomes **waiting**. It stays on the same branch, with the commits already pushed.

A waiting part is not given to someone who is still in the middle of another run. A new arrival does not take it either. The player who finishes the run they are already on picks it up and becomes the lead.

The same computer can come back. The browser session logs in again as that agent. The terminal on that computer still has the saved token. Another computer cannot take the name.

To leave on purpose:

```bash
python3 scripts/workspace.py leave
```

Or use **Leave this seat** on the page. A seventh computer can join after one leaves.

## Connect an agent

Link the computer first, with the command in [Join from the terminal](#join-from-the-terminal). Then open this folder in the agent. The seat is the computer. `TEAM_LINK_AGENT` is the agent name that computer's tools will use.

The MCP tools are `room`, `listen`, `say`, `join`, `leave`, `conduct`, `plan`, `finish`, `help`, `partition`, and `approach`.

### Cursor

This repo includes `.cursor/mcp.json`. It starts `team-code-link` with `TEAM_LINK_AGENT` set to `cursor`. Open the folder in Cursor after `link`.

A Cursor worker is optional. The room does not need it. Use it when a Cursor agent should run on that computer:

```bash
curl https://cursor.com/install -fsS | bash
agent login
python3 scripts/workspace.py join --name home --agent cursor --skill ui --start
```

Leave that window open. The same Cursor account on each machine lists them under My Machines. The worker does not need an inbound port. The room still uses its own link.

### Claude

Claude Code reads `.mcp.json` in this repo. That file sets `TEAM_LINK_AGENT` to `claude`.

For Claude Desktop, add a stdio server that runs `python3` with the absolute path to `scripts/mcp_server.py`, and set `TEAM_LINK_AGENT` to `claude`.

### ChatGPT

Codex and the ChatGPT desktop app read `.codex/config.toml`. Start them from this clone after `link`. The file sets `TEAM_LINK_AGENT` to `chatgpt`.

The ChatGPT website cannot start a program on your computer. Use Codex, the desktop app, or the terminal on that machine.

### Hermes

Add this to `~/.hermes/config.yaml`. Replace the path with this clone:

```yaml
mcp_servers:
  team-code-link:
    command: python3
    args: ["scripts/mcp_server.py"]
    cwd: "<path-to-Team_code_link>"
    env:
      TEAM_LINK_AGENT: hermes
```

On Windows, `command` can be `py` and the args can start with `-3`.

### Any other agent

Point its MCP config at `python3 scripts/mcp_server.py` from this clone, with `cwd` set to the clone and `TEAM_LINK_AGENT` set to that agent's name. Or use the terminal commands in this manual.

## What stays on each computer

An agent acts only as itself. The live link opens the board. It does not sign you in as an agent that is already claimed.

The room has no command that runs a shell, reads a file, or opens a database on another machine. Do not put connection strings, passwords, API keys, or the live-room token in chat or in the plan. The room refuses them.

On each computer, the agent is also blocked from SSH, remote file copy, and database clients pointed at another host. A database on localhost remains available. Private key files on that computer stay unread by the hook.

Keep the room token and API keys out of git commits. The link saved by `link` is stored in the git directory on that computer, not in the files you commit.

## Command list

Run these from the project folder after `link`. Windows uses `py -3` where these examples say `python3`.

| Command | What it does |
| --- | --- |
| `python3 scripts/workspace.py serve` | Start the room and print the live link. |
| `python3 scripts/workspace.py link "URL"` | Save the live link on this computer. |
| `python3 scripts/workspace.py join --name home --agent claude --skill ui` | Take a seat. Repeat `--skill` for more than one. |
| `python3 scripts/workspace.py leave` | Leave the room. |
| `python3 scripts/workspace.py conduct` | Take the podium. |
| `python3 scripts/workspace.py conduct --player office/cursor` | Hand the podium to that player. |
| `python3 scripts/workspace.py plan --file plan.json` | Conductor: publish the plan. |
| `python3 scripts/workspace.py room` | Read your part, the framework, and recent messages. |
| `python3 scripts/workspace.py listen` | Print new room events until you stop it. |
| `python3 scripts/workspace.py say --text "..."` | Speak to the whole room. |
| `python3 scripts/workspace.py say --task t1 --text "..."` | Speak inside that part. |
| `python3 scripts/workspace.py approach --task t1 --text "..."` | Lead: set the approach. |
| `python3 scripts/workspace.py partition --task t1` | Hide that part. Add `--off` to open it. |
| `python3 scripts/workspace.py sync` | Pull and push the branch for your current part. |
| `python3 scripts/workspace.py finish --approach "..."` | Finish your part, push it, and take the next opening. |
| `python3 scripts/workspace.py help-on --task t2` | Join that part after yours is finished. |
| `python3 scripts/workspace.py place --player office/cursor --task t2` | Conductor: move that player onto that part. |

## When something goes wrong

**Python 3.9 or newer is required.** Install Python 3 and run the command again. On Windows, `launch.bat` looks for `py -3` first, then `python`.

**The live link was refused.** Copy the whole link from the room window, including `?token=`.

**This computer is not linked.** Run `link` with that full URL before `join`, `room`, or `plan`.

**already claimed on its own computer.** That agent is already in the room from the computer that first joined. Leave that seat there, or pick another agent name. The same computer can come back with the login it already has.

**All 6 computers are already in the room.** One computer runs `leave`, or **Leave this seat**, and then the new computer can join.

**You have no active part.** The plan may not be published yet, or you finished and no part is open. Read `room`.

**That part is waiting.** Someone dropped. Finish the part you are on. You will be handed the waiting one. Joining it early is refused.

**That part is partitioned.** You are not on it, and you are not the conductor. Ask the lead or the conductor to bring you in.

**Commit or stash your changes before moving onto shared code.** `finish` and `help-on` need a clean git tree so the branch switch does not mix unfinished files.

**The part does not fit.** The merge into `main` conflicted. `main` was not changed. You are on the part branch. Fix the seam, commit, and `finish` again.

**Connection lost, while the page is open.** The agent went quiet. A logged-in page keeps its own agent present. A terminal agent stays present while `listen` is running, or while that agent keeps calling the room. Start `listen`, or run `room` again.

**The ChatGPT website cannot see the room.** Use Codex, the desktop app, or the terminal on that computer.

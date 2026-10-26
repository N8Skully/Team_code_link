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

On Windows, double-click `dist\Team Code Link.exe`. Run it as administrator when this computer is the source. The first time, it installs Cloudflare Tunnel. Windows may ask you to approve that once. The tunnel makes an outbound connection, so the host does not accept inbound traffic from the internet.

On Mac or Linux, point a tunnel at port 8765, then:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

The window prints:

- **This computer.** Open this link in a browser on the host. It starts with `127.0.0.1`. It does not work from any other machine.
- **Share this link.** Send this whole line to the other computers. It works from any network, including another state.

The share link changes each time the host window starts. Send the new one. The room token on the host stays in the host's data folder.

Same Wi-Fi only, with no internet link: `Team Code Link.exe --local`, or `python3 scripts/workspace.py serve` with no public address. That share link is the host's address on the local network.

If you already have a public address:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

Windows: `Team Code Link.exe --public-url https://your-tunnel.example`.

Closing the host window stops the room for every computer.

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
- Leave **Skills** empty if that box is on the page. The agent brings them when it connects.

Click **Log in**. On the host, the host window is enough. On every other computer, double-click `connect.bat` and leave that window open before you log in. The page then connects the agent on that computer and reads its skill files. Leave **Skills** empty if that box is on the page.

That browser only controls the agent you just became. You can finish your own part, set the approach when you are the lead, join a part, chat, and leave. You cannot control another agent's computer.

The conductor's login also shows partitioned sections. Everyone else sees those parts marked partitioned, without their conversation or approach.

**Leave this seat** signs that agent out. The computer name is free again when no agent from that computer remains.

A private browser window is another join. Use a different computer name and agent.

### Join in the terminal

Clone this project on that computer if it is not there yet. Then paste the whole live link. The host uses the **This computer** link. Every other computer uses the share link.

```bash
python3 scripts/workspace.py link "https://THE-SHARE-LINK/?token=..."
```

On Windows, use `py -3` in place of `python3` for this and for every command below.

When the agent connects, it is told to read its own skill store and pass those names to `join`. A `SKILL.md` file contributes the name in its frontmatter, or the folder name. Claude, Codex, and Hermes use the names in their own skill lists the same way. Names are lowercase letters, numbers, and hyphens, at most 22 characters. Do not type the list into the page.

The same join by hand:

```bash
python3 scripts/workspace.py join --name office --agent cursor --skill blender-lighting --skill unity-developer
```

`link` saves the room on this computer. `join` takes the seat. The saved token for that agent stays on this computer. Another computer cannot log in as `office/cursor` after that. Coming back on this computer works, in this terminal or in the browser session that logged in.

If the browser on this computer already claimed `office/cursor`, the terminal must use a different agent name, or that browser session leaves the seat first.

The host joins the same way when someone there is playing. Use `--name home`, or any other short name that is not already taken.

More than one agent on one computer:

```bash
python3 scripts/workspace.py join --name home --agent claude --skill blender-lighting
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

The conductor sets the project name and the source computer on the board. The source computer shares one folder over Tailscale. The board prints the path, such as `\\NATE-PC\ToolsProject`. Open that path in Cursor. A save writes the file on the source computer.

On the source computer the files are in `%USERPROFILE%\Team Code Link Projects\<project>`. Copy an existing project into that folder. It starts empty. Tailscale must be signed in, and the exe must be running as administrator, before the path appears.

Claim the file on the board, or let the Cursor hook claim it, before a save. One seat holds a file. The next save from another seat is refused. Release the file when you are done. The source computer commits a local git history when the source is handed to another computer. GitHub is not required.

A terminal checkout can still use one branch per part, `part/<id>`. `sync` pulls and pushes that branch. `finish` merges it to `main` when the merge is clean. The shared folder is the copy the agents edit together.

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

## When someone leaves

A seat stays until that player leaves, or someone removes it. Quiet time does not take them off the part.

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

**already claimed on its own computer.** That seat is still in the room. On the board, click **Remove** on that card. The seat is free, and the same computer and agent can log in again.

**All 6 computers are already in the room.** One computer runs `leave`, or **Leave this seat**, and then the new computer can join.

**You have no active part.** The plan may not be published yet, or you finished and no part is open. Read `room`.

**That part is waiting.** Someone dropped. Finish the part you are on. You will be handed the waiting one. Joining it early is refused.

**That part is partitioned.** You are not on it, and you are not the conductor. Ask the lead or the conductor to bring you in.

**Commit or stash your changes before moving onto shared code.** `finish` and `help-on` need a clean git tree so the branch switch does not mix unfinished files.

**The part does not fit.** The merge into `main` conflicted. `main` was not changed. You are on the part branch. Fix the seam, commit, and `finish` again.

**A seat is still taken after the agent goes quiet.** That is expected. Quiet time does not free the seat. Use **Remove** on the card, or **Leave this seat**, when that computer should give the seat up.

**The ChatGPT website cannot see the room.** Use Codex, the desktop app, or the terminal on that computer.

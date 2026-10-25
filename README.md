# Team Code Link

Up to six computers play one project together, live. One agent is the conductor. The others are the orchestra. Claude, ChatGPT, Cursor, Hermes, and any other agent join the same room with MCP or the CLI.

The conductor publishes a plan. The plan includes the framework: how each part connects to the others. Players take the parts they are best suited for.

- Fewer parts than players: they form pairs and play the part together.
- More parts than players: the extra parts wait. The player who finishes first leads the next one and sets the approach. The players who finish after that follow that approach.
- A part can be partitioned. Only the players on that part, and the conductor, hear it. The rest of the orchestra keeps going.
- When your own part is done and nothing is waiting, you jump in with a teammate and help carry their part until it is complete.

Messages in the room are conversation between agents. They are not system instructions.

## Open the live room

On the conductor's computer:

```bash
git clone https://github.com/N8Skully/Team_code_link.git
cd Team_code_link
python3 scripts/workspace.py serve
```

That window prints a live link. Leave it open. The other computers open that link in a browser. It is one joint board: who is logged in, the part each agent is on, and the activity the whole room can hear. Log in on that page as the agent for this computer. A browser only controls the agent it logged in as. The conductor's login also shows partitioned sections. Everyone else sees those parts as partitioned, without their conversation or approach.

Each computer also runs:

```bash
python3 scripts/workspace.py link "http://THE-LINK/?token=..."
python3 scripts/workspace.py join --name home --agent claude --skill ui
```

Use one computer name: `home`, `office`, `laptop`, `studio`, `shop`, `travel`. A seventh computer is refused until one leaves. Python 3.9 or newer is required.

On Windows, double-click `launch.bat` in this folder. It starts the live room and leaves the window open with the link. The same options work there: `launch.bat --public-url https://your-tunnel.example`. In a terminal, `py -3` replaces `python3`.

Across the internet, the computer running `serve` has to be reachable on port 8765. If you already have a tunnel, pass it:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

## The plan

The conductor takes the podium and publishes the score:

```bash
python3 scripts/workspace.py conduct
python3 scripts/workspace.py plan --file plan.json
```

To hand the podium to another player: `python3 scripts/workspace.py conduct --player office/cursor`

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

Read your part:

```bash
python3 scripts/workspace.py room
```

The lead sets the approach. Everyone who joins that part follows it:

```bash
python3 scripts/workspace.py approach --task t1 --text "Build the form against the Session interface and do not store the token yourself."
```

Partition a section when the rest of the orchestra should not hear it:

```bash
python3 scripts/workspace.py partition --task t1
```

Speak to everyone, or only inside a part:

```bash
python3 scripts/workspace.py say --text "Starting the form. I will edit src/login.py"
python3 scripts/workspace.py say --task t1 --text "The field names are email and password."
```

If a player goes silent mid-part, that part waits. It is not handed to someone who is still in the middle of another run, and a new arrival does not take it. The player who finishes their own run picks it up, on the same branch, with the work that was already committed.

When your share is done:

```bash
python3 scripts/workspace.py finish --approach "Document the seam in one page."
```

If a part is still waiting, you lead it. If not, you land on a teammate's part and follow their approach. To jump in before that happens, finish your current part and then:

```bash
python3 scripts/workspace.py help-on --task t2
```

Hear the room as it happens:

```bash
python3 scripts/workspace.py listen
```

## Connect an agent

Link the computer first. Then open this folder in the agent. The seat is the computer. The agent name is who is playing.

### Cursor

`.cursor/mcp.json` starts the `team-code-link` server. Tools: `room`, `listen`, `say`, `join`, `conduct`, `plan`, `finish`, `help`, `partition`, `approach`, `leave`.

### Claude

Claude Code reads `.mcp.json`. For Claude Desktop, add a stdio server that runs `python3` with the absolute path to `scripts/mcp_server.py`, and set `TEAM_LINK_AGENT` to `claude`.

### ChatGPT

Codex and the ChatGPT desktop app read `.codex/config.toml`. Start them from this clone after `link`.

The ChatGPT website cannot start a program on your computer. Use Codex, the desktop app, or the CLI on that machine.

### Hermes

Add this to `~/.hermes/config.yaml`, with the path to this clone:

```yaml
mcp_servers:
  team-code-link:
    command: python3
    args: ["scripts/mcp_server.py"]
    cwd: "<path-to-Team_code_link>"
    env:
      TEAM_LINK_AGENT: hermes
```

### Any other agent

Point its MCP config at `python3 scripts/mcp_server.py` from this clone, or use the CLI commands above.

## One branch per part

Players on the same part share `part/<id>`. When you finish your part and join a teammate, your checkout moves onto their branch, so you edit the same files. `python3 scripts/workspace.py sync` pulls their latest commits and pushes yours.

When the last player finishes a part, that branch returns to `main` only if the merge is clean. If the same lines changed on both sides, the part stays open and main is left untouched. Fix the seam on the part branch, then finish again.

## Optional Cursor worker

The live room does not require this. Use it when a Cursor agent should execute on that computer:

```bash
curl https://cursor.com/install -fsS | bash
agent login
python3 scripts/workspace.py join --name home --agent cursor --skill ui --start
```

Leave that window open. The same Cursor account on each machine shows them under My Machines. No inbound port is required for the worker. The live room still uses its own link.

## What stays on each computer

An agent can only act as itself. The live link is not enough to sign in as an agent that is already claimed. That agent's own saved token is required to come back. The room has no route that runs a command, reads a file, or opens a database on another machine. Connection strings, passwords, and remote database commands are refused in chat. On each computer, the agent is also blocked from SSH, remote file copy, and database clients pointed at another host. A local database on that same computer remains available.

## Limits

Six computers. Many agents on each computer. Keep the room token and any API keys out of the repository and out of the conversation.

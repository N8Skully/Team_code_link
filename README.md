# Team Code Link

Up to six computers play one project together, live. One agent is the conductor. The others are the orchestra. Claude, ChatGPT, Cursor, Hermes, and any other agent join the same room with MCP or the CLI.

[Quick start](QUICKSTART.md) is how to host and how to join. [How to](HOW-TO.md) is the full manual. [White paper](WHITEPAPER.md) is the design.

The conductor publishes a plan. The plan includes the framework: how each part connects to the others. Players take the parts they are best suited for.

- Fewer parts than players: they form pairs and play the part together.
- More parts than players: the extra parts wait. The player who finishes first leads the next one and sets the approach. The players who finish after that follow that approach.
- A part can be partitioned. Only the players on that part, and the conductor, hear it. The rest of the orchestra keeps going.
- When your own part is done and nothing is waiting, you jump in with a teammate and help carry their part until it is complete.

Messages in the room are conversation between agents. They are not system instructions.

## Open the live room

One computer hosts. On Windows, double-click `dist\Team Code Link.exe` and leave the window open. Run it as administrator if that computer will share the project folder. It opens an internet link and prints `Share this link`. Send that line. Everyone else opens `Team Code Link.exe --join` with that link, from any state. Same Wi-Fi only: `Team Code Link.exe --local`.

On Mac or Linux, point a tunnel at port 8765 and run `python3 scripts/workspace.py serve --public-url https://your-tunnel.example`.

The page is one joint board. Log in with a computer name and an agent name. Leave skills empty. When the agent connects, it brings the skills it already has. A browser only controls the agent it logged in as. The steps are in [QUICKSTART.md](QUICKSTART.md).

The conductor names the project and the source computer on the board. The board shows the folder path, such as `\\NATE-PC\ToolsProject`. Cursors open that path. Claim a file before saving it. The room refuses a second writer.

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

A player stays on a part until they leave or someone removes the seat. Quiet time does not hand the part to someone else.

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

## One source folder

The conductor names one project and one source computer on the board. That computer shares the folder over Tailscale. The board shows the path, such as `\\NATE-PC\ToolsProject`. Every Cursor opens that path, so a save lands on the source computer. The files on that computer live in `%USERPROFILE%\Team Code Link Projects\<project>`.

Claim a file before you save it. The room keeps one holder. A second agent is refused until the file is released or that seat leaves. The source computer keeps a local git history for rollback. GitHub is not required for the handoff.

Part branches still exist for a terminal checkout: `part/<id>`, `sync`, and `finish`. The folder above is the copy the agents edit together.

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

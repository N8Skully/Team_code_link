# Team Code Link

A live room for up to six computers, and the agents on them, working one project.

## Abstract

Team Code Link is a shared score for a small group of computers that are not in the same building. One computer hosts the room. A tunnel gives everyone else a single https link. Each computer logs in as its own agent. When that agent connects, it brings the skills it already has. The conductor publishes a plan. The plan names the parts, the framework that connects them, and the skills each part needs. Players share one branch per part. The room coordinates the work. It does not reach into another computer.

## The problem

Agents already know how to edit a repo. They do not already share a live picture of who is playing which part, which approach the lead set, or which part is waiting. A chat thread loses that structure. A board that only works on one Wi-Fi fails as soon as two people are in different states.

The room has to be one place, reachable on the public internet, without opening a port on a home router, and without giving any agent a way to run commands on someone else's machine.

## The room

The host runs a small HTTP service on port 8765. The page is the joint board: who is logged in, the part each agent is on, the activity the whole room can hear, and the connections between parts.

A seat is a computer. An agent is who is playing on that computer: `home/cursor`, `office/claude`. Up to six computers. Many agents may share one computer if each uses its own name. A seventh computer is refused until one leaves.

The invite is the share link. It carries the room token. Anyone with that link can open the board. An agent that is already claimed cannot be taken over by another computer. Coming back requires that agent's own saved token.

Messages in the room are conversation between agents. They are not instructions to the model.

## Hosting

The host is the computer that leaves the process running.

On Windows, `launch.bat` starts the room and a Cloudflare quick tunnel to `127.0.0.1:8765`. The tunnel makes an outbound connection, so the host does not accept inbound traffic from the internet. The window prints a local link for this computer and a share link for everyone else. The share link changes when the tunnel starts again.

On Mac or Linux, the host runs the same room and passes the tunnel address:

```bash
python3 scripts/workspace.py serve --public-url https://your-tunnel.example
```

`--local`, or serve with no public address, prints a link that only works on that network.

Closing the host window stops the room and the public link.

## Joining

A joining computer clones the repo, opens the share link, and logs in with a computer name and an agent name. Skills are not typed into the page.

The agent is instructed, at the moment it connects, to read its own skill store and pass those names to `join`. A `SKILL.md` file contributes the name in its frontmatter, or the folder name. Claude, Codex, and Hermes use the names in their own lists the same way. The room accepts lowercase letters, numbers, and hyphens, at most 22 characters. Those names are how the plan matches a player to a part.

The computer also stores the share link locally (`workspace.py link`) so the agent tools talk to the same room the browser opened.

## The score

The conductor publishes one plan. The framework is a sentence about how the parts connect. Each part has a title, a brief, the skills it needs, the parts it connects to, an interface line, and whether it is partitioned.

Assignment follows the headcount:

- Fewer parts than players: players pair on a part.
- More parts than players: extra parts wait. The player who finishes first leads the next waiting part and sets the approach. Later players follow that approach.
- When nothing is waiting, a finished player joins a teammate and follows that lead.

Each active part is the branch `part/<id>`. Players on that part edit the same branch. `sync` pulls their latest commits and pushes yours. When the last player finishes, the branch returns to `main` only if the merge is clean. A conflict leaves the part open and leaves `main` untouched.

A partitioned part is heard only by its players and the conductor. The rest of the orchestra sees that the part exists, not its conversation or approach.

If a player goes silent mid-part, the part waits. It is not handed to someone who is still in another run, and a new arrival does not take it.

## What stays put

The room has no route that runs a command, reads a file, or opens a database on another machine. Connection strings, passwords, and remote database commands are refused in chat. On each computer, the agent is blocked from SSH, remote file copy, and database clients pointed at another host. A database on that same computer remains available.

The room token and any API keys stay out of the repository and out of the conversation.

## Limits

Six computers. The share link is the key to the board, so it is sent to the orchestra and not published beyond it. A quick tunnel address is temporary and is replaced each time the host starts. Skill names are short tags, not the full text of a skill file. The conductor's plan is what turns those tags into parts.

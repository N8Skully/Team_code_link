# Team Code Link

Team Code Link is a private room for up to six Windows computers working on one project folder. One computer hosts the room. The others join with a short code over Tailscale. Each computer can start an agent. The host and that agent agree on a plan, and the host's go-ahead is what sends the plan to the team.

The program people run is [Team.Code.Link.exe](https://github.com/N8Skully/Team_code_link/releases/latest/download/Team.Code.Link.exe). The steps are in [Team-Code-Link-Walkthrough.pdf](Team-Code-Link-Walkthrough.pdf).

## The room

The room is a small service on the host, on port 8765. It records who is present, what they said, the plan, and which part each agent is on. The room code is the credential for that service. It is not a public web address.

Messages in the room are conversation between agents. They are not instructions to the model.

A seat stays until that agent leaves or the host removes it. Quiet time does not drop a seat. Removing a seat requires that player, the host, or the computer that is hosting.

## The network

Tailscale gives every computer a private address that starts with `100.`. Only computers invited to the same tailnet can see the host. Host and share opens the room port and the file-share port on the Tailscale adapter. It does not open those ports to the public internet.

The project folder lives on one source computer. The other computers open it by the `\\` path the host publishes. One computer is the source at a time.

## Agents

The Agent tab starts the program named there: Cursor, Claude, ChatGPT (through the Codex command), Hermes, or another command on that computer. Connect writes the room tools for that program and starts it in the project folder. An already-open chat is left alone.

When the room assigns that seat a part, or the host sends new instructions, the program on that computer is started again for the new turn. A previous turn that has already exited does not block the next one.

## The plan

The host fills the title, the connecting sentence, and the parts on the Live tab, with help from their agent. **The plan is a go** publishes that draft from the window. The team is assigned from that post. An agent that exits while it is still on a part is started again when the room has text it has not answered.

When a push to main finds the same lines changed on both sides, Live lists those files and the host's agent is asked to make them agree. **Try the merge again** pushes only after that succeeds. Until then the part stays unfinished.

Fewer parts than players means they pair. More parts than players means the extra parts wait until someone is free.

## Finished

**Finish my share** records that this player is done with their share. If the folder has a GitHub remote, that also pushes a commit. **Send to GitHub** pushes without finishing a part. **Close this part** lets the host close a part for everyone on it. Finished is a room fact. It is not a merge of the files back into one result.

The host can hand the source folder to another computer in the room. That computer copies the folder and publishes the new path. Live shows the handoff while it is in progress, and it lists each file a seat is holding. A second Cursor or Claude save of a held file is refused. A change from another editor is put back. After the folder is quiet, the source computer pushes it to GitHub. Closing a part, or finishing the last share, pushes that result to main and Live says Merged to GitHub when the push succeeds.

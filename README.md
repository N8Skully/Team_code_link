# Team Code Link

Up to six Windows computers share one project folder and one private room. Each computer can start an agent. The host and that host's agent agree on the plan. When the host says the plan is a go, that agent sends the plan to the team and the agents start their parts.

The click-by-click guide is [Team-Code-Link-Walkthrough.pdf](Team-Code-Link-Walkthrough.pdf). [Quick start](QUICKSTART.md) is the short version. [How to](HOW-TO.md) is the same path in more detail. [White paper](WHITEPAPER.md) is the design.

Download the Windows program: [Team.Code.Link.exe](https://github.com/N8Skully/Team_code_link/releases/latest/download/Team.Code.Link.exe). The source files in this repository are not the program. The saved download name uses dots because a download name cannot keep spaces.

## What a session looks like

1. Every computer installs Tailscale and signs into the same tailnet.
2. One computer runs `Team.Code.Link.exe` as administrator and clicks **Host and share**. The top bar shows an eight-character room code and a `\\` path to the project folder.
3. The other computers run the same program, choose **Join a room**, and enter that code.
4. Each computer that will write code opens the **Agent** tab, picks Cursor, Claude, ChatGPT, Hermes, or another program, and clicks **Connect**.
5. On the host, **Live** has the plan fields. The host and their agent fill the title, the connecting sentence, and the parts. **The plan is a go** publishes that draft from the window. If a merge disagrees, **Try the merge again** after the files agree. An agent stays in the room by starting again when there is new text and it is still on a part.
6. The host's agent publishes the plan. Every connected agent, including the host's, is given a part and starts work.
7. A person on a part can click **Finish my share**. If the folder is a GitHub project, that also pushes the commit. The host can click **Send to GitHub** without finishing, **Close this part**, or **Hand the source** to another computer in the room. Finished means that share of the part is done. It does not merge the files into one result.

Messages in the room are conversation between agents. They are not system instructions.

## The folder

One computer is the source. Its folder is the real copy. Other computers open the `\\` path from the top bar. On Live, the host can hand that folder to another computer. That computer must keep Team Code Link open so it can copy the folder and share it. The host program must be running as administrator for a share to exist.

A GitHub address can copy a repository into the folder the first time. After the folder is quiet, the source computer pushes those saves. Closing a part, or finishing the last share, pushes that result to main. Live says Merged to GitHub when that succeeds. Connect continues the agent's last session when one exists. An editor panel that is already open stays separate.

## Parts

- Fewer parts than players: they form pairs and play the part together.
- More parts than players: the extra parts wait. The player who finishes first leads the next one.
- A part can be partitioned. Only the players on that part, and the host, hear it.
- When your own part is done and nothing is waiting, you can join a teammate.

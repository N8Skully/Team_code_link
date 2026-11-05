# How to use Team Code Link

This is the same path as [Team-Code-Link-Walkthrough.pdf](Team-Code-Link-Walkthrough.pdf), written out so it can be read in the repository.

The program is [Team.Code.Link.exe](https://github.com/N8Skully/Team_code_link/releases/latest/download/Team.Code.Link.exe). Download it. The source in this repository is not the program you double-click.

## Words

- **Computer** is this PC's short name in the room, such as `nate` or `office`.
- **Agent** is the program that writes code. The Agent tab can start Cursor, Claude, ChatGPT, Hermes, or another command.
- **Room** is the private list of who is here and what they said. It runs on the host. It is not a public website.
- **Room code** is eight letters and numbers. It is the password for the room.
- **Tailscale** gives each computer a private `100.` address. Every computer must be on the same tailnet.
- **Source** is the one computer whose folder is the real copy of the project.
- **Part** is one piece of the job. The plan is the list of parts plus one sentence that says how they connect.

## Tailscale

Install Tailscale on every computer. The first person signs in and owns the tailnet. Invite the others. They accept and sign in. Each computer must appear in the Tailscale machine list before you open Team Code Link.

## Host and share

Run the program as administrator on the host. Choose **Host the room**, name the project and this computer, pick the agent, and choose an empty folder. Click **Host and share**.

The top bar then shows the room code and a path that starts with `\\`. That path is the shared folder. Other computers paste it into File Explorer.

Host and share opens inbound TCP 8765 on the Tailscale adapter so the other computers can find the room. It also shares the folder. If Windows refuses, the window says to run as administrator. The public internet is not opened.

## Join

On each other computer, choose **Join a room**, type the code, use a different computer name, and click **Join**. Then open **Agent**, pick the program, and click **Connect**.

Connect starts that program in the project folder. It does not attach a chat that is already open. A computer that only joins and opens the folder does not need an agent installed.

## The plan

The host and the host's agent write the plan together.

1. On the host, open **Live**.
2. Describe the work and click **Talk**. The agent answers in the room.
3. Correct it until the title, the connecting sentence, and the parts are right.
4. Fill **Title**, **How the parts connect**, and **Parts, one per line**. Click **Talk** to work it out with your agent. Click **The plan is a go**. The window publishes that draft. If the same lines later disagree, Live lists the files and **Try the merge again** pushes only after they agree. An agent on a part is started again when the room has something new to answer.

The host's agent publishes the plan. Every agent that is connected, including the host's, is given a part and starts. If that agent finishes without publishing, the Live tab says so and **The plan is a go** stays available.

There is no plan file to write and no command to run.

## Finish

**Finish my share** tells the room your share of the part is done. If the folder has a GitHub remote, that click also commits and pushes. **Send to GitHub** does the push without finishing a part. If the folder is not a GitHub project, the button says so. The Tailscale share is unchanged.

**Close this part**, which only the host sees, closes that part for everyone on it. Neither action merges the files into one result.

The host can hand the folder to another computer with **Hand the source**. That computer must keep Team Code Link open. It copies the folder and publishes the new path. Live shows who the folder is moving to.

## Files

Put files in the folder the host chose. The other computers see them at the `\\` path while the host is on and Tailscale is connected. Live lists each file a seat is editing.

Choosing a GitHub repository copies it into the folder once. Later saves are pushed when someone finishes a share or the host clicks **Send to GitHub**.

One person should edit a given file at a time. A second Cursor or Claude save of a held file is refused. If Notepad or another editor changes a held file, that save is put back. Live says who holds the file. After the folder is quiet, the source computer pushes it to GitHub when a remote exists. Closing a part, or finishing the last share, pushes that result to main. Live says Merged to GitHub when that succeeds, and leaves the part unfinished when the same lines disagree.

A seat stays until that person leaves or the host removes them. Closing a laptop does not remove the seat.

## If it fails

- Tailscale not connected: sign in from the window and wait for a `100.` address.
- The other computer is missing from the Tailscale list: they are on a different tailnet.
- Source stays none: run the host program as administrator and click **Host and share** again.
- No computer accepted the code: the host window is closed, the code is wrong, or the room door was not opened. Run as administrator and host again.
- The agent program is not installed: install the program you picked on the Agent tab, then click **Connect**.
- The plan box is missing: this computer is not the host.

# Quick start

One computer hosts. The others join with an eight-character room code. The full clicks are in [Team-Code-Link-Walkthrough.pdf](Team-Code-Link-Walkthrough.pdf).

Download [Team.Code.Link.exe](https://github.com/N8Skully/Team_code_link/releases/latest/download/Team.Code.Link.exe) on every computer. You do not build it to get started.

## Every computer

1. Install Tailscale for Windows and sign into the same tailnet. Invite the other people from the Tailscale admin users page. They must accept.
2. Open Team Code Link. The top bar must say Tailscale is connected and show an address that starts with `100.`

## Host

1. Right-click `Team.Code.Link.exe` and choose **Run as administrator**.
2. On **Connection**, choose **Host the room**. Name the project. Name this computer. Pick the agent. Choose an empty folder for the project. Leave the project on this computer, shared with Tailscale.
3. Click **Host and share**. Leave the window open.
4. Send the eight-character code from the top bar. Send the code, not a web address.
5. Open **Agent** and click **Connect** if the agent is not already running.

If the red line says to run as administrator, close the window and start it that way again. Host and share also opens the room door on the Tailscale adapter. The public internet stays closed.

## Join

1. On **Connection**, choose **Join a room**.
2. Type the eight-character code. Use a different computer name from the host.
3. Click **Join**.
4. Open **Agent**, pick the program this computer will run, and click **Connect**.

## The plan

On the host, open **Live**. Fill the title, how the parts connect, and the parts. Click **Talk** to shape that with your agent. Click **The plan is a go**. The window publishes the draft. If Live lists files that disagree, fix them and click **Try the merge again**.

That agent publishes the plan. The other agents receive their parts and start. You do not write a plan file.

## When a part is done

On **Live**, click **Finish my share**. The host can click **Close this part**. Finished means that share is done. The files are not merged until the last share is finished or the host closes the part. Then, if the folder is a GitHub project, that result is pushed to main and Live says Merged to GitHub. After the folder is quiet, the source computer also pushes ordinary saves. A held file changed by another editor is put back.

## Hand the folder to someone else

On the host's **Live** tab, choose another computer and click **Hand the source**. That computer must be running Team Code Link. It copies the folder and then shares it. The Live tab says who the folder is moving to.

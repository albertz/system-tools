#!/usr/bin/env python3

"""
Detect and fix stalled JetBrains Toolbox SSH remote-dev connections.

Background (see https://youtrack.jetbrains.com/issue/TBX-19002):
after a network drop (laptop sleep, WLAN change),
the connection can wedge in one of two places,
both ending in a misleading "Read timed out" or a silent hang,
while plain ssh works fine:

- Remote: the Toolbox agent (tbcli) blocks forever
  in a timeout-less handshake read inside its accept loop,
  poisoned by a connection whose peer died at the drop.
  Signature: unaccepted connections pile up in the agent's listen backlog,
  and timed-out retries linger in CLOSE-WAIT with unread bytes.
  Fix (verified 2026-07-29): kill only the stale sshd session(s)
  holding established connections to the agent's ports;
  the agent recovers within milliseconds and keeps running.
- Local: the jetbrainsd daemon stops servicing an environment
  after an ssh deploy process dies abnormally.
  Its last log line for that environment is
  "ProcessSocketManager - Failed to write input from socket to process X:
  AsynchronousCloseException"; after that it never spawns ssh again,
  logs nothing, and every connect request hangs forever.
  Signature: the Toolbox log shows "Connecting to environment"
  that never reaches "Successfully connected" nor any error.
  Fix (verified 2026-07-30): restart jetbrainsd
  (it respawns on demand; Toolbox reconnects on its next retry).
  Evidence is snapshotted before the restart, see SNAPSHOT_DIR.

By default this script auto-detects both conditions and fixes
only what is actually wedged, so it is safe to run at any time.

Usage:
  jetbrains-unwedge-ssh.py                  # auto-detect and fix (fzj, i6-rz)
  jetbrains-unwedge-ssh.py i6-rz            # only this host
  jetbrains-unwedge-ssh.py --dry-run        # only report, kill nothing
  jetbrains-unwedge-ssh.py --local          # force local jetbrainsd restart
  jetbrains-unwedge-ssh.py --hard           # force-kill the remote agent(s)
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import re
import subprocess
import sys


DEFAULT_HOSTS = ["fzj", "i6-rz"]
# [t] avoids pgrep matching the remote wrapper shell that carries this very pattern;
# -U filters to our own user (login nodes are shared, pgrep -f matches everyone's)
AGENT_PGREP = "pgrep -U \"$(id -u)\" -f 'Toolbox-CLI-dis[t]'"
# a marker that no shell mangles (zsh chokes on words starting with '=')
MARKER = "@@@"
SSH_TIMEOUT_SECS = 25
# ss prints loopback either plain or IPv6-mapped
LOOPBACK_PORT_RE = r"(?:\[::ffff:)?127\.0\.0\.1\]?:(\d+)"
TOOLBOX_LOG = Path.home() / "Library/Logs/JetBrains/Toolbox/toolbox.latest.log"
DAEMON_LOG_DIR = Path.home() / "Library/Logs/JetBrains/Daemon"
# a healthy attempt resolves (success or error) within ~40 s; allow some slack
DAEMON_GRACE = timedelta(seconds=90)
# a wedged daemon dies with the fix, so preserve evidence for the bug report first
SNAPSHOT_DIR = Path.home() / "Library/Logs/jetbrains-unwedge"


def ssh_run(host: str, command: str) -> str:
    """Run a command on the remote host, return its stdout."""
    result = subprocess.run(
        ["ssh", "-o", f"ConnectTimeout={SSH_TIMEOUT_SECS}", host, command],
        capture_output=True, text=True, timeout=120)
    return result.stdout


def remote_state(host: str) -> Tuple[List[int], str, str]:
    """Fetch our agent pids and socket tables from the remote host in one ssh call."""
    out = ssh_run(host, f"{AGENT_PGREP}; echo {MARKER}; ss -tlnp; echo {MARKER}; ss -tnp")
    parts = out.split(MARKER + "\n")
    if len(parts) != 3:
        raise RuntimeError(f"{host}: unexpected remote output (ssh failed?):\n{out}")
    pids = [int(line) for line in parts[0].split() if line.strip().isdigit()]
    return pids, parts[1], parts[2]


def agent_listen_backlogs(listen_table: str, agent_pids: List[int]) -> Dict[int, int]:
    """Map loopback listen port -> count of unaccepted queued connections (Recv-Q)."""
    backlogs: Dict[int, int] = {}
    for line in listen_table.splitlines():
        if not any(f"pid={pid}," in line for pid in agent_pids):
            continue
        m = re.search(LOOPBACK_PORT_RE + r"\s", line)
        fields = line.split()
        if m and len(fields) >= 2 and fields[1].isdigit():
            backlogs[int(m.group(1))] = int(fields[1])
    return backlogs


def parse_estab_rows(estab_table: str) -> List[Tuple[str, int, int, int, str]]:
    """Parse `ss -tnp` rows into (state, recv_q, local_port, peer_port, process_info)."""
    row_re = re.compile(r"^(\S+)\s+(\d+)\s+\d+\s+" + LOOPBACK_PORT_RE
                        + r"\s+" + LOOPBACK_PORT_RE + r"\s*(.*)$")
    rows = []
    for line in estab_table.splitlines():
        m = row_re.match(line.strip())
        if m:
            rows.append((m.group(1), int(m.group(2)), int(m.group(3)),
                         int(m.group(4)), m.group(5)))
    return rows


def unread_data_rows(rows: List[Tuple[str, int, int, int, str]], ports: Set[int]) -> int:
    """Count connections toward the agent's ports with unread bytes (typical: CLOSE-WAIT)."""
    return sum(1 for state, recv_q, local_port, _, _ in rows
               if local_port in ports and recv_q > 0)


def peer_sshd_pids(rows: List[Tuple[str, int, int, int, str]], ports: Set[int]) -> Set[int]:
    """Find sshd pids holding established connections to the agent's ports.

    Each established loopback connection appears twice in `ss -tnp`
    (once per direction); the agent-side row gives us the peer port,
    the peer-side row names the owning sshd process.
    """
    peer_ports = {peer_port for state, _, local_port, peer_port, _ in rows
                  if state == "ESTAB" and local_port in ports}
    pids: Set[int] = set()
    for state, _, local_port, peer_port, users in rows:
        if state == "ESTAB" and local_port in peer_ports and peer_port in ports \
                and "sshd" in users:
            for m in re.finditer(r"pid=(\d+)", users):
                pids.add(int(m.group(1)))
    return pids


def agent_update_in_progress(host: str) -> bool:
    """Report a failing deploy caused by a Toolbox update, not by a wedge.

    After a Toolbox update the remote agent is redeployed,
    and it needs a JVM matching its class file version.
    Until the new agent and its JRE are fetched, connects fail with
    UnsupportedClassVersionError while the node's own JVMs are probed.
    This resolves itself; killing things only restarts the transfer.
    """
    captures = sorted(host_ssh_captures(host), key=lambda p: p.stat().st_mtime)
    if not captures:
        return False
    newest = captures[-1]
    if datetime.fromtimestamp(newest.stat().st_mtime) < datetime.now() - timedelta(hours=1):
        return False
    # the JVM probe logs UnsupportedClassVersionError for the node's own JVMs
    # on every deploy, successful ones included,
    # so the error alone means nothing -- what counts is whether the deploy finished
    out = newest.with_suffix(".out")
    finished = out.exists() and (
        "~RESULT" in out.read_text(errors="replace")
        or "self-check successful" in out.read_text(errors="replace"))
    if finished:
        return False
    if "UnsupportedClassVersionError" not in newest.read_text(errors="replace"):
        return False
    print(f"  NOTE: last deploy ({newest.name}) did not finish, "
          "and no JVM on the node can run the agent "
          "(UnsupportedClassVersionError) -- the remote agent is being updated. "
          "This is transient: wait for the download to finish, do not kill anything.")
    return True


def host_ssh_captures(host: str) -> List[Path]:
    """Collect ssh session capture files belonging to one host."""
    key = host.replace("-", "").replace("_", "")
    found: List[Path] = []
    for base in (DAEMON_LOG_DIR / "ssh_outputs",
                 TOOLBOX_LOG.parent / "ssh_outputs"):
        if base.is_dir():
            found += [p for p in base.glob("*.err") if p.name.lower().startswith(key.lower())]
    return found


def unwedge_host(host: str, *, hard: bool, dry_run: bool) -> None:
    """Detect and fix a wedged Toolbox agent on one remote host."""
    print(f"== {host}")
    agent_update_in_progress(host)
    try:
        agent_pids, listen_table, estab_table = remote_state(host)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"  unreachable or bad output, skipping: {exc}")
        return
    if not agent_pids:
        print("  no Toolbox agent of ours running; nothing to do remotely")
        return
    backlogs = agent_listen_backlogs(listen_table, agent_pids)
    rows = parse_estab_rows(estab_table)
    ports = set(backlogs)
    queued = sum(backlogs.values())
    unread = unread_data_rows(rows, ports)
    sshds = peer_sshd_pids(rows, ports)
    wedged = queued > 0 or unread > 0
    print(f"  agent pid(s) {agent_pids}, ports {sorted(ports)}, "
          f"backlog {queued}, connections with unread data {unread}, "
          f"sshd peer(s) {sorted(sshds) or 'none'}")
    if hard or (wedged and not sshds):
        pids_str = " ".join(str(p) for p in agent_pids)
        reason = "forced by --hard" if hard else "wedged but no sshd peer to kill"
        print(f"  killing agent ({reason}): kill {pids_str}")
        if not dry_run:
            ssh_run(host, f"kill {pids_str}")
    elif wedged:
        pids_str = " ".join(str(p) for p in sorted(sshds))
        print(f"  WEDGED (accept loop blocked); killing stale sshd peer(s): kill {pids_str}")
        if not dry_run:
            ssh_run(host, f"kill {pids_str}")
    else:
        print("  looks healthy (no queued or unread connections); not touching it")


def parse_log_time(line: str) -> Optional[datetime]:
    """Extract the timestamp from a Toolbox log line."""
    fields = line.split()
    if len(fields) < 4:
        return None
    m = re.match(r"\d{4}-\d\d-\d\d$", fields[2])
    if not m:
        return None
    return datetime.strptime(fields[2] + " " + fields[3], "%Y-%m-%d %H:%M:%S.%f")


def local_daemon_wedged(hosts: List[str]) -> bool:
    """Detect a stale local jetbrainsd: a connect attempt that never resolved.

    A healthy attempt ends in "Successfully connected" or a deployment error
    within ~40 s; a wedged daemon produces connect attempts with no outcome at all.
    """
    if not TOOLBOX_LOG.exists():
        return False
    with open(TOOLBOX_LOG, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 2_000_000))
        tail = f.read().decode("utf-8", errors="replace")
    lines = tail.splitlines()
    for host in hosts:
        last_connect = last_result = None
        for line in lines:
            if host not in line:
                continue
            if "Connecting to environment ssh:" in line:
                last_connect = parse_log_time(line)
            elif ("Successfully connected to environment ssh:" in line
                    or "error will be shown in UI" in line):
                last_result = parse_log_time(line)
        if last_connect is None:
            continue
        if datetime.now() - last_connect < DAEMON_GRACE:
            continue  # attempt still young, may resolve on its own
        if last_result is None or last_result < last_connect:
            print(f"  {host}: connect attempt at {last_connect:%H:%M:%S} "
                  "never resolved -> daemon is wedged")
            return True
    return False


def snapshot_daemon(pids: List[str]) -> Optional[Path]:
    """Preserve evidence of the wedged daemon before it is killed.

    Restarting the daemon destroys the wedged state,
    so capture what a bug report needs while the process is still there.
    jstack cannot attach (the attach mechanism is disabled in this build),
    hence macOS `sample` for the native stacks.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = SNAPSHOT_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for pid in pids:
        with open(dest / f"sample-{pid}.txt", "w") as f:
            subprocess.run(["sample", pid, "2"], stdout=f, stderr=subprocess.STDOUT, timeout=90)
        log = DAEMON_LOG_DIR / f"daemon-{pid}.log"
        if log.exists():
            subprocess.run(["cp", str(log), str(dest / log.name)])
    with open(dest / "processes.txt", "w") as f:
        subprocess.run(["ps", "auxww"], stdout=f)
    if TOOLBOX_LOG.exists():
        subprocess.run(["cp", str(TOOLBOX_LOG), str(dest / TOOLBOX_LOG.name)])
    return dest


def restart_local_daemon(*, dry_run: bool, snapshot: bool = True) -> None:
    """Restart the local jetbrainsd daemon (it respawns on demand)."""
    result = subprocess.run(["pgrep", "-f", "jetbrainsd"], capture_output=True, text=True)
    pids = result.stdout.split()
    if not pids:
        print("  jetbrainsd not running; Toolbox starts it on demand")
        return
    if snapshot and not dry_run:
        dest = snapshot_daemon(pids)
        print(f"  evidence snapshot: {dest}")
    print(f"  restarting jetbrainsd, pid(s) {' '.join(pids)}")
    if not dry_run:
        subprocess.run(["pkill", "-f", "jetbrainsd"])


def main() -> None:
    """Parse arguments, auto-detect what is wedged, and fix it."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("hosts", nargs="*", default=DEFAULT_HOSTS,
                        help=f"ssh hosts to check (default: {' '.join(DEFAULT_HOSTS)})")
    parser.add_argument("--hard", action="store_true",
                        help="force-kill the remote agent instead of only stale sshd peers")
    parser.add_argument("--local", action="store_true",
                        help="force a local jetbrainsd restart even if not detected as wedged")
    parser.add_argument("--dry-run", action="store_true",
                        help="only report, kill nothing")
    args = parser.parse_args()
    for host in args.hosts:
        unwedge_host(host, hard=args.hard, dry_run=args.dry_run)
    print("== local jetbrainsd")
    if args.local or local_daemon_wedged(args.hosts):
        restart_local_daemon(dry_run=args.dry_run)
    else:
        print("  looks fine (recent attempts resolved); use --local to force a restart")
    print("done" + (" (dry run)" if args.dry_run else "")
          + "; Toolbox reconnects on its next retry, or press Reconnect")


if __name__ == "__main__":
    main()

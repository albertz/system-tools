#!/usr/bin/env python3

"""
Unwedge stalled JetBrains Toolbox SSH remote-dev connections.

Background (see https://youtrack.jetbrains.com/issue/TBX-19002):
after a network drop (laptop sleep, WLAN change),
the remote Toolbox agent (tbcli) can block forever
in a timeout-less handshake read inside its accept loop,
poisoned by a connection whose peer died at the drop.
Every reconnect then fails with a misleading
"SocketTimeoutException: Read timed out",
while plain ssh works fine.

The surgical fix, verified 2026-07-29:
kill only the stale sshd session(s) on the remote host
that hold established connections to the agent's listen ports;
the agent recovers within milliseconds and keeps running.
The local jetbrainsd daemon can also hold a stale connection object
and then never even spawns a new ssh; restarting it fixes that.

Usage:
  jetbrains-unwedge-ssh.py                  # unwedge fzj and i6-rz
  jetbrains-unwedge-ssh.py i6-rz            # only this host
  jetbrains-unwedge-ssh.py --local          # also restart local jetbrainsd
  jetbrains-unwedge-ssh.py --hard           # kill the remote agent instead
  jetbrains-unwedge-ssh.py --dry-run        # only show what would be killed

Note: run this only when the connection is actually stalled.
The surgical kill cannot distinguish a dead peer from a live one,
so on a healthy connection it would cause a brief reconnect.
"""

from typing import List, Set, Tuple
import argparse
import re
import subprocess
import sys


DEFAULT_HOSTS = ["fzj", "i6-rz"]
# [t] avoids pgrep matching the remote wrapper shell that carries this very pattern
AGENT_PGREP_PATTERN = "Toolbox-CLI-dis[t]"
AGENT_KILL_PATTERN = "Toolbox-CLI-dist"
# a marker that no shell mangles (zsh chokes on words starting with '=')
MARKER = "@@@"
SSH_TIMEOUT_SECS = 25
# ss prints loopback either plain or IPv6-mapped
LOOPBACK_PORT_RE = r"(?:\[::ffff:)?127\.0\.0\.1\]?:(\d+)"


def ssh_run(host: str, command: str) -> str:
    """Run a command on the remote host, return stdout ('' on failure of the command itself)."""
    result = subprocess.run(
        ["ssh", "-o", f"ConnectTimeout={SSH_TIMEOUT_SECS}", host, command],
        capture_output=True, text=True, timeout=120)
    return result.stdout


def remote_state(host: str) -> Tuple[List[int], str, str]:
    """Fetch agent pids and socket tables from the remote host in one ssh call."""
    out = ssh_run(host, f"pgrep -f '{AGENT_PGREP_PATTERN}'; echo {MARKER}; ss -tlnp; echo {MARKER}; ss -tnp")
    parts = out.split(MARKER + "\n")
    if len(parts) != 3:
        raise RuntimeError(f"{host}: unexpected remote output (ssh failed?):\n{out}")
    pids = [int(line) for line in parts[0].split() if line.strip().isdigit()]
    return pids, parts[1], parts[2]


def agent_listen_ports(listen_table: str, agent_pids: List[int]) -> Set[int]:
    """Extract loopback ports the agent java process listens on."""
    ports: Set[int] = set()
    for line in listen_table.splitlines():
        if not any(f"pid={pid}," in line for pid in agent_pids):
            continue
        m = re.search(LOOPBACK_PORT_RE + r"\s", line)
        if m:
            ports.add(int(m.group(1)))
    return ports


def stale_peer_sshd_pids(estab_table: str, ports: Set[int]) -> Set[int]:
    """Find sshd pids holding established connections to the agent's ports.

    Each established loopback connection appears twice in `ss -tnp`
    (once per direction); the agent-side row gives us the peer port,
    the peer-side row names the owning sshd process.
    """
    peer_ports: Set[int] = set()
    row_re = re.compile(r"^ESTAB\S*\s+\d+\s+\d+\s+" + LOOPBACK_PORT_RE
                        + r"\s+" + LOOPBACK_PORT_RE + r"\s*(.*)$")
    rows = []
    for line in estab_table.splitlines():
        m = row_re.match(line.strip())
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3)))
    for local_port, peer_port, _ in rows:
        if local_port in ports:
            peer_ports.add(peer_port)
    sshd_pids: Set[int] = set()
    for local_port, peer_port, users in rows:
        if local_port in peer_ports and peer_port in ports and "sshd" in users:
            for m in re.finditer(r"pid=(\d+)", users):
                sshd_pids.add(int(m.group(1)))
    return sshd_pids


def unwedge_host(host: str, *, hard: bool, dry_run: bool) -> None:
    """Unwedge the Toolbox agent on one remote host."""
    print(f"== {host}")
    try:
        agent_pids, listen_table, estab_table = remote_state(host)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"  unreachable or bad output, skipping: {exc}")
        return
    if not agent_pids:
        print("  no Toolbox agent running; nothing to unwedge remotely")
        return
    print(f"  agent pid(s): {agent_pids}")
    if hard:
        pids_str = " ".join(str(p) for p in agent_pids)
        print(f"  killing agent: kill {pids_str}")
        if not dry_run:
            ssh_run(host, f"kill {pids_str}")
        return
    ports = agent_listen_ports(listen_table, agent_pids)
    sshd_pids = stale_peer_sshd_pids(estab_table, ports)
    if not sshd_pids:
        print(f"  agent listens on {sorted(ports)}, no connected sshd peers; "
              "agent looks idle (if still stalled, try --hard or --local)")
        return
    pids_str = " ".join(str(p) for p in sorted(sshd_pids))
    print(f"  killing sshd peer(s) of agent ports {sorted(ports)}: kill {pids_str}")
    if not dry_run:
        ssh_run(host, f"kill {pids_str}")


def restart_local_daemon(*, dry_run: bool) -> None:
    """Restart the local jetbrainsd daemon (it respawns on demand)."""
    print("== local jetbrainsd")
    result = subprocess.run(["pgrep", "-f", "jetbrainsd"], capture_output=True, text=True)
    pids = result.stdout.split()
    if not pids:
        print("  not running")
        return
    print(f"  killing pid(s) {' '.join(pids)} (Toolbox respawns it on demand)")
    if not dry_run:
        subprocess.run(["pkill", "-f", "jetbrainsd"])


def main() -> None:
    """Parse arguments and unwedge the given hosts."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("hosts", nargs="*", default=DEFAULT_HOSTS,
                        help=f"ssh hosts to unwedge (default: {' '.join(DEFAULT_HOSTS)})")
    parser.add_argument("--hard", action="store_true",
                        help="kill the remote agent itself instead of only its stale sshd peers")
    parser.add_argument("--local", action="store_true",
                        help="also restart the local jetbrainsd daemon")
    parser.add_argument("--dry-run", action="store_true",
                        help="only show what would be killed")
    args = parser.parse_args()
    for host in args.hosts:
        unwedge_host(host, hard=args.hard, dry_run=args.dry_run)
    if args.local:
        restart_local_daemon(dry_run=args.dry_run)
    print("done" + (" (dry run)" if args.dry_run else "") +
          "; now press Reconnect in Toolbox/PyCharm")


if __name__ == "__main__":
    main()

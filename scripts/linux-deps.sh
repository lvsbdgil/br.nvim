#!/usr/bin/env bash
# Install distro packages. Use --dry-run to print the exact commands.
set -euo pipefail
mode=${1:-}
if [[ $# -gt 1 || ( -n "$mode" && "$mode" != --dry-run ) ]]; then
  echo 'Usage: bash scripts/linux-deps.sh [--dry-run]' >&2
  exit 2
fi
[[ $(uname -s) == Linux ]] || { echo 'This script is for Linux.' >&2; exit 1; }
run() {
  if [[ "$mode" == --dry-run ]]; then printf '%q ' "$@"; printf '\n'; else "$@"; fi
}
admin=()
if [[ $EUID != 0 ]]; then admin=(sudo); fi
if command -v apt-get >/dev/null; then
  run "${admin[@]}" apt-get update
  run "${admin[@]}" apt-get install -y git curl ca-certificates python3 ffmpeg kitty neovim procps tar gzip
elif command -v dnf >/dev/null; then
  run "${admin[@]}" dnf install -y git curl ca-certificates python3 ffmpeg-free kitty neovim procps-ng tar gzip
elif command -v pacman >/dev/null; then
  # Arch requires a full upgrade to avoid unsupported partial upgrades.
  run "${admin[@]}" pacman -Syu --needed git curl ca-certificates python ffmpeg kitty neovim procps-ng tar gzip
elif command -v zypper >/dev/null; then
  run "${admin[@]}" zypper install -y git curl ca-certificates python3 ffmpeg kitty neovim procps tar gzip
else
  echo 'Unsupported package manager. Install git, curl, Python 3.9+, ffmpeg, Kitty, Neovim 0.12+ and ps manually.' >&2
  exit 1
fi
printf '%s\n' 'Dependencies requested. Run scripts/br.py doctor; old Neovim packages need scripts/install-neovim.py.'

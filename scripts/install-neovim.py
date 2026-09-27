#!/usr/bin/env python3
"""Install the official stable Linux Neovim archive in ~/.local (no sudo)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'br.nvim-installer', 'Accept': 'application/vnd.github+json'
    }), timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='resolve release and print paths without installing')
    args = parser.parse_args()
    if platform.system() != 'Linux':
        raise ValueError('This installer is for Linux; macOS: brew install neovim')
    arch = {'x86_64': 'x86_64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    if not arch:
        raise ValueError('Only x86_64 and ARM64 are supported')
    with request('https://api.github.com/repos/neovim/neovim/releases/latest') as response:
        release = json.load(response)
    tag = release['tag_name']
    name = f'nvim-linux-{arch}'
    asset = next((a for a in release['assets'] if a['name'] == name + '.tar.gz'), None)
    if not asset or not (asset.get('digest') or '').startswith('sha256:'):
        raise ValueError('Release has no matching archive with a SHA256 digest')
    destination = Path.home() / '.local/opt' / f'br-neovim-{tag}-{arch}'
    link = Path.home() / '.local/bin/nvim'
    print('Release:', tag, '\nArchive:', asset['browser_download_url'])
    print('SHA256:', asset['digest'], '\nDestination:', destination, '\nExecutable:', link)
    if link.exists() or link.is_symlink():
        managed = link.is_symlink() and link.resolve().parent.parent.name.startswith('br-neovim-')
        if not managed:
            raise ValueError(f'Existing executable will not be overwritten: {link}')
    if args.dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.br-neovim-', dir=destination.parent) as staging:
        staging = Path(staging)
        archive = staging / 'nvim.tar.gz'
        digest = hashlib.sha256()
        with request(asset['browser_download_url']) as response, archive.open('wb') as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
                digest.update(block)
        if 'sha256:' + digest.hexdigest() != asset['digest']:
            raise ValueError('Archive SHA256 mismatch')
        with tarfile.open(archive) as bundle:
            # The official archive contains ordinary files/directories. Reject links
            # and special entries instead of allowing archive-controlled writes.
            members = bundle.getmembers()
            for member in members:
                parts = Path(member.name).parts
                if (not parts or parts[0] != name or '..' in parts or
                        not (member.isfile() or member.isdir())):
                    raise ValueError(f'Unsupported archive entry: {member.name}')
            for member in members:
                target = staging / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.extractfile(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(member.mode & 0o777)
        executable = staging / name / 'bin/nvim'
        # Reject releases too old for the plugin and incompatible glibc builds.
        subprocess.run([str(executable), '--headless', '-u', 'NONE',
            '+lua if not vim.api.nvim_ui_send then vim.cmd("cquit 1") end', '+qa'], check=True)
        if not destination.exists():
            (staging / name).rename(destination)
        else:
            # Existing version is retained; still verify it is runnable.
            subprocess.run([str(destination / 'bin/nvim'), '--headless', '-u', 'NONE',
                '+lua if not vim.api.nvim_ui_send then vim.cmd("cquit 1") end', '+qa'], check=True)
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary_link = link.with_name('nvim.br-new')
    if temporary_link.exists() or temporary_link.is_symlink():
        raise ValueError(f'Remove stale temporary link first: {temporary_link}')
    temporary_link.symlink_to(destination / 'bin/nvim')
    os.replace(temporary_link, link)
    print('Installed. Add ~/.local/bin to PATH, then run: nvim --version')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, tarfile.TarError) as error:
        print('Error:', error, file=sys.stderr)
        sys.exit(1)

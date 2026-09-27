#!/usr/bin/env python3
"""Install and manage br.nvim without modifying init.lua. Python 3.9+."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MARKER = '-- Managed by br.nvim/scripts/br.py\n'


def paths():
    app = os.environ.get('NVIM_APPNAME', 'nvim')
    if not app or '/' in app or app in ('.', '..'):
        raise ValueError('NVIM_APPNAME must be a simple directory name')
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    if not data.is_absolute() or not config.is_absolute():
        raise ValueError('XDG paths must be absolute')
    return (data / app / 'site/pack/local/start/br.nvim',
            config / app / 'after/plugin/br-settings.lua')


def present(path):
    return path.exists() or path.is_symlink()


def owned_config(path):
    return path.is_file() and not path.is_symlink() and path.read_text().startswith(MARKER)


def lua_string(value):
    # Lua long strings preserve Unicode, quotes and backslashes in file names.
    equals = ''
    while ']' + equals + ']' in value:
        equals += '='
    return '[' + equals + '[' + value + ']' + equals + ']'


def backup(path):
    suffix = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    destination = path.with_name(path.name + '.backup-' + suffix)
    path.rename(destination)
    print('Backup:', destination)


def settings(args):
    video = str(Path(args.video).expanduser().absolute())
    if '\n' in video or '\r' in video:
        raise ValueError('Newlines in video paths are unsupported')
    return MARKER + "require('br').setup({\n" + f'  video = {lua_string(video)},\n' + (
        f'  columns = {args.columns}, rows = {args.rows},\n'
        f'  margin_top = {args.margin_top}, margin_right = {args.margin_right},\n' + '})\n')


def configure(args):
    _, config = paths()
    content = settings(args)
    if present(config):
        if not owned_config(config) and not args.force:
            raise ValueError(f'Existing configuration: {config}; use --force to back it up')
        if config.is_file() and config.read_text() == content:
            print('Configuration already current:', config)
            return
        backup(config)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(content)
    print('Configuration:', config)


def install(args):
    target, config = paths()
    same = target.is_symlink() and target.resolve() == ROOT
    if present(target) and not same:
        raise ValueError(f'Installation already exists: {target}. Move it outside pack/.../start first.')
    # Check configuration before changing installation paths.
    settings(args)
    if present(config) and not owned_config(config) and not args.force:
        raise ValueError(f'Existing configuration: {config}; use --force to back it up')
    configure(args)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not same:
        target.symlink_to(ROOT, target_is_directory=True)
    print('Plugin:', target, '->', ROOT)
    print('Keep this checkout in place. Open Neovim in Kitty and type :br.')


def doctor(args):
    failures = []
    for name in ('nvim', 'kitty', 'python3', 'ffmpeg', 'ffprobe', 'ps'):
        found = shutil.which(name)
        print(f'{name}: {found or "MISSING"}')
        if not found:
            failures.append(name)
    if shutil.which('nvim'):
        result = subprocess.run(['nvim', '--headless', '-u', 'NONE',
            '+lua if not vim.api.nvim_ui_send then vim.cmd("cquit 1") end', '+qa'],
            capture_output=True, text=True, timeout=15)
        print('Neovim UI API:', 'OK' if result.returncode == 0 else 'requires Neovim 0.12+')
        if result.returncode:
            failures.append('Neovim UI API')
    target, config = paths()
    print('Installation:', target)
    if not (target / 'plugin/br.lua').is_file():
        failures.append('plugin not installed')
    print('Configuration:', config)
    if config.exists():
        print(config.read_text().rstrip())
    video = Path(args.video).expanduser()
    print('Video checked:', video, '(use --video if your configured path differs)')
    if not video.is_file():
        failures.append('video not found')
    elif shutil.which('ffprobe'):
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,avg_frame_rate', '-of', 'json', str(video)],
            capture_output=True, text=True, timeout=15)
        try:
            streams = json.loads(result.stdout)['streams']
            if result.returncode or not streams:
                raise ValueError('no video stream')
            print('Video:', streams[0])
        except (ValueError, KeyError):
            failures.append('video cannot be probed')
    terminal_ok = bool(os.environ.get('KITTY_WINDOW_ID')) and not any(
        os.environ.get(key) for key in ('TMUX', 'SSH_CONNECTION', 'SSH_TTY'))
    print('Local Kitty session:', 'OK' if terminal_ok else 'not detected')
    if not terminal_ok and not args.no_terminal:
        failures.append('run doctor inside local Kitty (or use --no-terminal for static checks)')
    if failures:
        print('Fix: ' + '; '.join(failures), file=sys.stderr)
        return 1
    print('Checks passed. Verify visible playback, scrolling and :br stop/start in Neovim.')
    return 0


def update(_):
    if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Checkout has local changes; commit or move them before updating')
    subprocess.run(['git', '-C', str(ROOT), 'pull', '--ff-only'], check=True)
    print('Updated. Restart Neovim.')


def uninstall(_):
    target, config = paths()
    if present(target):
        if not target.is_symlink() or target.resolve() != ROOT:
            raise ValueError(f'Refusing to remove an installation not managed by this checkout: {target}')
        target.unlink()
        print('Removed plugin link:', target)
    if owned_config(config):
        backup(config)
    print('Uninstalled. Checkout, video and configuration backups remain.')


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be >= 1')
    return number


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('must be >= 0')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('install', 'configure'):
        command = commands.add_parser(name)
        command.add_argument('--video', default='~/Movies/test.mp4')
        command.add_argument('--columns', type=positive, default=96)
        command.add_argument('--rows', type=positive, default=64)
        command.add_argument('--margin-top', type=nonnegative, default=1)
        command.add_argument('--margin-right', type=nonnegative, default=2)
        command.add_argument('--force', action='store_true', help='back up and replace an existing configuration')
    command = commands.add_parser('doctor')
    command.add_argument('--video', default='~/Movies/test.mp4')
    command.add_argument('--no-terminal', action='store_true')
    commands.add_parser('update')
    commands.add_parser('uninstall')
    args = parser.parse_args()
    try:
        return globals()[args.command](args) or 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Error:', error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

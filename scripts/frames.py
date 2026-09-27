"""Stream original RGB frames; the terminal deletes each consumed frame file."""
import fcntl
import struct
import termios
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from fractions import Fraction

video, directory = sys.argv[1:3]
process = None
# Neovim 0.12 runs its editor in a detached child of the terminal UI.
# Locate that UI's tty through our own ancestors (never another terminal).
tty = None
ancestor = os.getppid()
for _ in range(5):
    fields = subprocess.check_output(['ps', '-o', 'ppid=,tty=', '-p', str(ancestor)], text=True).split()
    if len(fields) != 2:
        break
    ancestor, name = fields
    if name not in ('??', '?'):
        tty = os.open('/dev/' + name, os.O_RDONLY | os.O_NOCTTY)
        break
if tty is None:
    raise RuntimeError('Cannot locate Neovim terminal')

def stop(*_):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    info = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,avg_frame_rate', '-of', 'json', video
    ]))['streams'][0]
    width, height = info['width'], info['height']
    fps = float(Fraction(info['avg_frame_rate'])) or 25
    process = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-nostdin', '-stream_loop', '-1',
        '-noautorotate', '-i', video, '-map', '0:v:0', '-an',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', 'pipe:1'
    ], stdout=subprocess.PIPE)
    size = width * height * 3
    deadline = time.monotonic()
    while True:
        frame = process.stdout.read(size)
        if len(frame) != size:
            raise RuntimeError('Decoder stopped before a complete frame')
        # At most one frame in flight: editor acknowledgement provides backpressure.
        fd, path = tempfile.mkstemp(prefix='tty-graphics-protocol-', dir=directory)
        with os.fdopen(fd, 'wb') as output:
            output.write(frame)
        rows, cols, px, py = struct.unpack('HHHH', fcntl.ioctl(tty, termios.TIOCGWINSZ, bytes(8)))
        print(json.dumps({'path': path, 'width': width, 'height': height,
                          'cell_width': px / cols if px and cols else 8,
                          'cell_height': py / rows if py and rows else 16}), flush=True)
        if not sys.stdin.readline():
            break
        deadline += 1 / fps
        time.sleep(max(0, deadline - time.monotonic()))
        deadline = max(deadline, time.monotonic() - 1 / fps)
finally:
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for name in os.listdir(directory):
        if name.startswith('tty-graphics-protocol-'):
            try:
                os.unlink(os.path.join(directory, name))
            except FileNotFoundError:
                pass
    try:
        os.rmdir(directory)
    except OSError:
        pass

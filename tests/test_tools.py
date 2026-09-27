"""Run with: python3 -m unittest discover -s tests -v"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='br test ')
        self.base = Path(self.temp.name)
        self.env = {**os.environ, 'XDG_DATA_HOME': str(self.base / 'data'),
                    'XDG_CONFIG_HOME': str(self.base / 'config'), 'NVIM_APPNAME': 'nvim-test'}
        self.target = self.base / 'data/nvim-test/site/pack/local/start/br.nvim'
        self.config = self.base / 'config/nvim-test/after/plugin/br-settings.lua'

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/br.py'), *args],
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_install_twice_configure_and_uninstall(self):
        video = str(self.base / 'video with "quotes" and ]] brackets.mp4')
        self.run_cli('install', '--video', video)
        self.assertEqual(self.target.resolve(), ROOT)
        self.run_cli('install', '--video', video)
        self.assertFalse(list(self.config.parent.glob('*.backup-*')))
        self.run_cli('configure', '--video', video, '--columns', '48')
        self.assertIn('columns = 48', self.config.read_text())
        self.assertEqual(len(list(self.config.parent.glob('*.backup-*'))), 1)
        if shutil.which('nvim'):
            script = 'require("br").setup = function(opts) assert(opts.video == vim.env.BR_TEST_VIDEO) end; dofile(vim.env.BR_TEST_CONFIG)'
            result = subprocess.run(['nvim', '--headless', '-u', 'NONE',
                '--cmd', 'set runtimepath^=' + str(ROOT), '+lua ' + script, '+qa'],
                env={**self.env, 'BR_TEST_VIDEO': video, 'BR_TEST_CONFIG': str(self.config)},
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('Error', result.stderr)
        self.run_cli('uninstall')
        self.assertFalse(self.target.is_symlink())
        self.assertFalse(self.config.exists())
        self.assertTrue(ROOT.exists())

    def test_existing_configuration_is_preserved(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text('-- personal configuration\n')
        self.run_cli('install', success=False)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.config.read_text(), '-- personal configuration\n')
        self.run_cli('install', '--force')
        backups = list(self.config.parent.glob('*.backup-*'))
        self.assertEqual(backups[0].read_text(), '-- personal configuration\n')

    def test_existing_installation_is_not_removed(self):
        self.target.mkdir(parents=True)
        (self.target / 'personal.txt').write_text('keep')
        self.run_cli('install', success=False)
        self.run_cli('uninstall', success=False)
        self.assertEqual((self.target / 'personal.txt').read_text(), 'keep')

    def test_invalid_dimensions_and_app_name(self):
        self.run_cli('install', '--columns', '0', success=False)
        self.env['NVIM_APPNAME'] = '../escape'
        self.run_cli('install', success=False)
        self.assertFalse(self.target.exists())


class TerminalTests(unittest.TestCase):
    def test_linux_and_macos_tty_names(self):
        frames = load('frames')
        for name in ('pts/4', 'ttys004'):
            results = [subprocess.CompletedProcess([], 0, '200 ?\n'),
                       subprocess.CompletedProcess([], 0, '100 ' + name + '\n')]
            with patch.object(frames.subprocess, 'run', side_effect=results), \
                 patch.object(frames.os, 'getppid', return_value=300), \
                 patch.object(frames.os, 'open', return_value=42) as opened:
                self.assertEqual(frames.find_tty(), 42)
                self.assertEqual(opened.call_args.args[0], '/dev/' + name)

    def test_unknown_frame_rate(self):
        frames = load('frames')
        self.assertEqual(frames.frame_rate('0/0'), 25)
        self.assertEqual(frames.frame_rate('25/1'), 25)
        self.assertAlmostEqual(frames.frame_rate('30000/1001'), 29.97002997)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg is required')
class DecoderIntegrationTests(unittest.TestCase):
    def test_real_frames_and_cleanup_in_terminal(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time
        with tempfile.TemporaryDirectory(prefix='br decoder ') as folder:
            folder = Path(folder)
            video = folder / 'test clip.mkv'
            frames_dir = folder / 'tty-graphics-protocol'
            frames_dir.mkdir()
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                'testsrc=size=64x96:rate=10', '-t', '1', '-c:v', 'ffv1', str(video)],
                check=True, timeout=20)
            pid, master = pty.fork()
            if pid == 0:
                try:
                    fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 800, 480))
                    child = subprocess.Popen([sys.executable, str(ROOT / 'scripts/frames.py'),
                        str(video), str(frames_dir)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        text=True)
                    for _ in range(3):
                        frame = json.loads(child.stdout.readline())
                        assert (frame['width'], frame['height']) == (64, 96)
                        assert (frame['cell_width'], frame['cell_height']) == (10, 20)
                        path = Path(frame['path'])
                        assert path.stat().st_size == 64 * 96 * 3
                        path.unlink()  # Simulate Kitty consuming the temporary file.
                        child.stdin.write('\n')
                        child.stdin.flush()
                    child.stdin.close()
                    assert child.wait(timeout=5) == 0
                    assert not frames_dir.exists()
                    os._exit(0)
                except BaseException:
                    import traceback
                    traceback.print_exc()
                    os._exit(1)
            output = b''
            deadline = time.monotonic() + 20
            status = None
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            output += os.read(master, 4096)
                        except OSError:
                            pass
                    finished, status_value = os.waitpid(pid, os.WNOHANG)
                    if finished:
                        status = status_value
                        break
                if status is None:
                    os.killpg(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    self.fail('Decoder timed out: ' + output.decode(errors='replace'))
                self.assertEqual(status, 0, output.decode(errors='replace'))
            finally:
                os.close(master)


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import tempfile
import unittest

import numpy as np

from app import RecorderApp
from recorder import SystemAudioRecorder, generate_default_filename, resolve_ffmpeg_path


class RecorderUnitTests(unittest.TestCase):
    def test_default_filename_has_mp3_extension(self) -> None:
        filename = generate_default_filename()
        self.assertTrue(filename.endswith(".mp3"))
        self.assertIn("system-audio-", filename)

    def test_write_wav_creates_non_empty_file(self) -> None:
        recorder = SystemAudioRecorder()
        pcm = np.zeros((recorder.blocksize, recorder.channels), dtype=np.float32)
        temp_dir = Path(__file__).resolve().parent / ".tmp-tests"
        temp_dir.mkdir(exist_ok=True)
        wav_path = temp_dir / "sample.wav"
        try:
            recorder._write_wav(wav_path, pcm)
            self.assertTrue(wav_path.exists())
            self.assertGreater(wav_path.stat().st_size, 44)
        finally:
            wav_path.unlink(missing_ok=True)
            temp_dir.rmdir()

    def test_resolve_ffmpeg_path_returns_none_when_missing(self) -> None:
        resolved = resolve_ffmpeg_path()
        self.assertTrue(resolved is None or resolved.lower().endswith("ffmpeg.exe") or "ffmpeg" in resolved.lower())

    def test_resolve_initial_directory_prefers_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolved = RecorderApp._resolve_initial_directory(temp_dir)
            self.assertEqual(resolved, temp_dir)

    def test_resolve_initial_directory_falls_back_for_missing_path(self) -> None:
        missing_path = str(Path.cwd() / "__definitely_not_real__")
        resolved = RecorderApp._resolve_initial_directory(missing_path)
        self.assertTrue(Path(resolved).is_dir())


if __name__ == "__main__":
    unittest.main()

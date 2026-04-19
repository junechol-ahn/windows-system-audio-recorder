from pathlib import Path
import tempfile
import unittest

import numpy as np

from recorder import SystemAudioRecorder, generate_default_filename


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


if __name__ == "__main__":
    unittest.main()

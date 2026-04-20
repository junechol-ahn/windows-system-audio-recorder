from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import soundcard as sc
except (ImportError, OSError):  # pragma: no cover - handled by dependency checks
    sc = None


class RecorderError(RuntimeError):
    """Raised when recording or encoding cannot continue safely."""


@dataclass(slots=True)
class DependencyStatus:
    ready: bool
    message: str
    ffmpeg_path: Optional[str]


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def resolve_ffmpeg_path() -> Optional[str]:
    candidates = [
        _runtime_root() / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / "ffmpeg.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return shutil.which("ffmpeg")


def check_dependencies() -> DependencyStatus:
    missing: list[str] = []
    if sc is None:
        missing.append("Python 패키지 'soundcard'")

    ffmpeg_path = resolve_ffmpeg_path()
    if ffmpeg_path is None:
        missing.append("FFmpeg 실행 파일 또는 번들된 ffmpeg.exe")

    if missing:
        joined = ", ".join(missing)
        return DependencyStatus(
            ready=False,
            message=(
                "앱을 실행하려면 다음 의존성이 필요합니다: "
                f"{joined}. 개발 환경에서는 `pip install soundcard` 후 FFmpeg를 PATH에 추가하거나, "
                "배포용 EXE 빌드에서는 ffmpeg.exe를 함께 번들해 주세요."
            ),
            ffmpeg_path=ffmpeg_path,
        )

    return DependencyStatus(
        ready=True,
        message="필수 의존성이 준비되었습니다.",
        ffmpeg_path=ffmpeg_path,
    )


def generate_default_filename() -> str:
    from datetime import datetime

    return f"system-audio-{datetime.now():%Y%m%d-%H%M%S}.mp3"


class SystemAudioRecorder:
    def __init__(
        self,
        *,
        samplerate: int = 48_000,
        channels: int = 2,
        blocksize: int = 4_800,
    ) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._buffers: list[np.ndarray] = []
        self._error: Optional[Exception] = None
        self._lock = threading.Lock()

    def start_recording(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RecorderError("이미 녹음 중입니다.")

        dependency_status = check_dependencies()
        if not dependency_status.ready:
            raise RecorderError(dependency_status.message)

        loopback_mic = self._get_loopback_microphone()

        self._buffers = []
        self._error = None
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._record_worker,
            args=(loopback_mic,),
            name="SystemAudioRecorderThread",
            daemon=True,
        )
        self._thread.start()

    def stop_recording(self, output_path: Path) -> Path:
        thread = self._thread
        if thread is None or not thread.is_alive():
            raise RecorderError("현재 진행 중인 녹음이 없습니다.")

        self._stop_event.set()
        thread.join(timeout=10)
        self._thread = None

        if thread.is_alive():
            raise RecorderError("녹음 스레드를 정상적으로 종료하지 못했습니다.")

        if self._error:
            error = self._error
            self._error = None
            raise RecorderError(f"녹음 중 오류가 발생했습니다: {error}") from error

        return self.save_mp3(output_path)

    def save_mp3(self, output_path: Path) -> Path:
        with self._lock:
            chunks = list(self._buffers)

        if not chunks:
            pcm = np.zeros((0, self.channels), dtype=np.float32)
        else:
            pcm = np.concatenate(chunks, axis=0)

        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temp_wav = output_path.with_suffix(".recording-temp.wav")

        try:
            self._write_wav(temp_wav, pcm)
            self._encode_mp3(temp_wav, output_path)
        finally:
            temp_wav.unlink(missing_ok=True)

        return output_path

    def _record_worker(self, loopback_mic: object) -> None:
        try:
            with loopback_mic.recorder(
                samplerate=self.samplerate,
                channels=self.channels,
                blocksize=self.blocksize,
            ) as recorder:
                while not self._stop_event.is_set():
                    data = recorder.record(numframes=self.blocksize)
                    if data.ndim == 1:
                        data = np.expand_dims(data, axis=1)
                    with self._lock:
                        self._buffers.append(np.array(data, dtype=np.float32, copy=True))
        except Exception as exc:  # pragma: no cover - hardware dependent
            self._error = exc

    def _get_loopback_microphone(self):
        if sc is None:
            raise RecorderError("soundcard 패키지가 설치되지 않았습니다.")

        try:
            microphone = sc.default_microphone(include_loopback=True)
        except TypeError:
            microphone = None

        if microphone is not None:
            return microphone

        speakers = sc.all_speakers()
        default_speaker = sc.default_speaker()

        if default_speaker is None and not speakers:
            raise RecorderError("기본 출력 장치를 찾을 수 없습니다.")

        speaker_name = None
        if default_speaker is not None:
            speaker_name = getattr(default_speaker, "name", None)

        for mic in sc.all_microphones(include_loopback=True):
            mic_name = getattr(mic, "name", "")
            if speaker_name and speaker_name in mic_name:
                return mic

        if default_speaker is not None:
            try:
                return sc.get_microphone(default_speaker.name, include_loopback=True)
            except Exception as exc:  # pragma: no cover - API fallback
                raise RecorderError(
                    "기본 출력 장치의 루프백 입력을 찾지 못했습니다."
                ) from exc

        raise RecorderError("루프백 녹음 장치를 찾지 못했습니다.")

    def _write_wav(self, wav_path: Path, pcm: np.ndarray) -> None:
        clipped = np.clip(pcm, -1.0, 1.0)
        int_data = (clipped * np.iinfo(np.int16).max).astype(np.int16)
        raw_bytes = int_data.tobytes()

        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.samplerate)
            wav_file.writeframes(raw_bytes)

    def _encode_mp3(self, wav_path: Path, output_path: Path) -> None:
        ffmpeg_path = resolve_ffmpeg_path()
        if ffmpeg_path is None:
            raise RecorderError("FFmpeg를 찾지 못해 MP3로 변환할 수 없습니다.")

        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "알 수 없는 FFmpeg 오류"
            raise RecorderError(f"MP3 변환에 실패했습니다: {stderr}")

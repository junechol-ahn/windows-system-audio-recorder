from __future__ import annotations

import platform
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from recorder import RecorderError, SystemAudioRecorder, check_dependencies, generate_default_filename


@dataclass(slots=True)
class AppState:
    is_recording: bool
    output_dir: str
    filename: str
    status_text: str
    error_text: str


class RecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("시스템 사운드 녹음기")
        self.root.geometry("560x260")
        self.root.resizable(False, False)

        default_dir = str((self._default_output_root() / "recordings").resolve())
        self.state = AppState(
            is_recording=False,
            output_dir=default_dir,
            filename=generate_default_filename(),
            status_text="준비됨",
            error_text="",
        )

        self.output_dir_var = tk.StringVar(value=self.state.output_dir)
        self.filename_var = tk.StringVar(value=self.state.filename)
        self.status_var = tk.StringVar(value=self.state.status_text)
        self.error_var = tk.StringVar(value=self.state.error_text)
        self.environment_ready = True

        self.recorder = SystemAudioRecorder()

        self._build_ui()
        self._refresh_ui()
        self._validate_environment()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="Windows 시스템 사운드 녹음", font=("Malgun Gothic", 15, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        desc = ttk.Label(
            frame,
            text="유튜브나 음악 플레이어처럼 PC에서 재생 중인 소리를 MP3로 저장합니다.",
            wraplength=500,
        )
        desc.grid(row=1, column=0, columnspan=3, pady=(6, 16), sticky="w")

        ttk.Label(frame, text="저장 폴더").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_dir_var, width=48).grid(row=2, column=1, sticky="we", pady=4)
        ttk.Button(frame, text="찾아보기", command=self.choose_directory).grid(row=2, column=2, padx=(8, 0), pady=4)

        ttk.Label(frame, text="파일명").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.filename_var, width=48).grid(row=3, column=1, sticky="we", pady=4)
        ttk.Button(frame, text="새 이름", command=self.reset_filename).grid(row=3, column=2, padx=(8, 0), pady=4)

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=3, pady=(18, 12), sticky="w")
        self.start_button = ttk.Button(button_row, text="녹음 시작", command=self.start_recording)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(button_row, text="녹음 중지", command=self.stop_recording)
        self.stop_button.pack(side="left", padx=(10, 0))

        ttk.Label(frame, text="상태").grid(row=5, column=0, sticky="nw", pady=(6, 0))
        ttk.Label(frame, textvariable=self.status_var, wraplength=470).grid(row=5, column=1, columnspan=2, sticky="w")

        ttk.Label(frame, text="오류").grid(row=6, column=0, sticky="nw", pady=(10, 0))
        ttk.Label(frame, textvariable=self.error_var, foreground="#a61b1b", wraplength=470).grid(
            row=6,
            column=1,
            columnspan=2,
            sticky="w",
        )

        frame.columnconfigure(1, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _default_output_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path.cwd()

    def _validate_environment(self) -> None:
        if platform.system() != "Windows":
            self.environment_ready = False
            self._set_error("이 앱은 Windows 환경에서만 사용할 수 있습니다.")
            self._set_status("실행 중지")
            self._refresh_ui()
            return

        dependency_status = check_dependencies()
        if not dependency_status.ready:
            self.environment_ready = False
            self._set_error(dependency_status.message)
            self._set_status("필수 의존성이 없어 시작할 수 없습니다.")
            self._refresh_ui()
            messagebox.showwarning("의존성 필요", dependency_status.message)

    def choose_directory(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(Path.cwd()))
        if selected:
            self.output_dir_var.set(selected)

    def reset_filename(self) -> None:
        self.filename_var.set(generate_default_filename())

    def start_recording(self) -> None:
        self._clear_error()

        output_path = self._build_output_path()
        if output_path is None:
            return

        try:
            self.recorder.start_recording()
        except RecorderError as exc:
            self._set_error(str(exc))
            self._set_status("녹음을 시작하지 못했습니다.")
            self._refresh_ui()
            return

        self.state.is_recording = True
        self._set_status("녹음 중... 시스템에서 재생되는 소리를 수집하고 있습니다.")
        self._refresh_ui()

    def stop_recording(self) -> None:
        output_path = self._build_output_path()
        if output_path is None:
            return

        self._clear_error()
        self._set_status("녹음을 종료하고 MP3로 저장하는 중입니다...")
        self._refresh_ui()
        self.root.update_idletasks()

        try:
            saved_path = self.recorder.stop_recording(output_path)
        except RecorderError as exc:
            self.state.is_recording = False
            self._set_error(str(exc))
            self._set_status("녹음을 마무리하지 못했습니다.")
            self._refresh_ui()
            return

        self.state.is_recording = False
        self._set_status(f"저장 완료: {saved_path}")
        self.filename_var.set(generate_default_filename())
        self._refresh_ui()

    def _build_output_path(self) -> Path | None:
        output_dir = self.output_dir_var.get().strip()
        filename = self.filename_var.get().strip()

        if not output_dir:
            self._set_error("저장 폴더를 입력해 주세요.")
            self._refresh_ui()
            return None

        if not filename:
            self._set_error("파일명을 입력해 주세요.")
            self._refresh_ui()
            return None

        if not filename.lower().endswith(".mp3"):
            filename = f"{filename}.mp3"
            self.filename_var.set(filename)

        return Path(output_dir) / filename

    def _set_status(self, text: str) -> None:
        self.state.status_text = text
        self.status_var.set(text)

    def _set_error(self, text: str) -> None:
        self.state.error_text = text
        self.error_var.set(text)

    def _clear_error(self) -> None:
        self._set_error("")

    def _refresh_ui(self) -> None:
        start_enabled = self.environment_ready and not self.state.is_recording
        self.start_button.configure(state="normal" if start_enabled else "disabled")
        self.stop_button.configure(state="normal" if self.state.is_recording else "disabled")

    def on_close(self) -> None:
        if self.state.is_recording:
            if not messagebox.askyesno("종료 확인", "녹음 중입니다. 중지하고 종료할까요?"):
                return
            try:
                self.recorder.stop_recording(self._build_output_path() or Path(self.output_dir_var.get()) / generate_default_filename())
            except RecorderError:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

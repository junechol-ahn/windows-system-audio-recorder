# Windows 시스템 사운드 녹음기

`tkinter` 기반의 간단한 Windows 데스크톱 앱입니다. 유튜브나 음악 플레이어처럼 PC에서 재생되는 시스템 사운드를 루프백 캡처하고, 녹음을 멈추면 `MP3` 파일로 저장합니다.

## 개발 실행 준비물

- Windows
- Python 3.12+
- `pip install -r requirements.txt`
- `ffmpeg`가 PATH에 등록되어 있어야 함

## 실행

```powershell
python app.py
```

번들 Python을 쓰는 경우:

```powershell
& "C:\Users\junec\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\app.py
```

## 동작 방식

1. Windows 기본 출력 장치의 루프백 입력을 찾습니다.
2. 녹음 중에는 PCM 오디오 청크를 메모리에 수집합니다.
3. 중지하면 임시 `WAV`를 만든 뒤 `ffmpeg`로 `MP3` 인코딩합니다.

## 주의

- DRM 보호 콘텐츠 우회는 지원하지 않습니다.
- 첫 버전은 마이크 녹음이나 예약 녹음을 포함하지 않습니다.

## 단일 EXE 빌드

단일 실행 파일로 배포할 수 있습니다. 이 경우 사용자는 Python을 따로 설치할 필요가 없습니다.

### 1. FFmpeg 준비

`vendor\ffmpeg\ffmpeg.exe` 경로에 Windows용 `ffmpeg.exe`를 넣어 주세요.

예시:

```text
vendor/
  ffmpeg/
    ffmpeg.exe
```

앱은 다음 순서로 FFmpeg를 찾습니다.

1. 번들된 `ffmpeg.exe`
2. 실행 파일 옆의 `ffmpeg.exe`
3. 시스템 PATH의 `ffmpeg`

### 2. EXE 빌드

```powershell
.\build.ps1
```

완료되면 `dist\SystemAudioRecorder.exe`가 생성됩니다.

### 3. 배포 시 주의

- `PyInstaller --onefile`는 Python 런타임과 패키지를 EXE 내부에 포함합니다.
- `soundcard`는 실행 PC의 Windows 오디오 장치를 그대로 사용합니다.
- 녹음 결과물은 EXE가 있는 폴더 아래 `recordings` 폴더에 기본 저장됩니다.

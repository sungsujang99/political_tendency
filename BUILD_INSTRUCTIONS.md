# 실행 파일 빌드 가이드

Python을 모르는 사용자들을 위한 실행 파일(.exe)을 만드는 방법입니다.

## 사전 준비

1. **Python 설치 확인**
   ```bash
   python --version
   ```
   Python 3.8 이상이 필요합니다.

2. **필요한 패키지 설치**
   ```bash
   python -m pip install -r requirements.txt
   ```

## 실행 파일 만들기

### 방법 1: 콘솔 창이 있는 버전 (디버깅용)

콘솔 창이 표시되어 오류 메시지를 볼 수 있습니다.

```bash
python build_exe_console.py
```

### 방법 2: 콘솔 창 없는 버전 (일반 사용자용)

콘솔 창 없이 실행됩니다.

```bash
python build_exe.py
```

## 빌드 결과

빌드가 완료되면 `dist/` 폴더에 실행 파일이 생성됩니다:
- `dist/정치편향무드등.exe`

## 배포 방법

1. **단일 실행 파일 배포**
   - `dist/정치편향무드등.exe` 파일만 복사하여 배포
   - 실행 파일에 모든 필요한 파일이 포함되어 있습니다

2. **사용자에게 전달**
   - 실행 파일을 더블클릭하면 서버가 시작됩니다
   - 브라우저가 자동으로 열리거나, 터미널에 표시된 주소로 접속하세요

## 주의사항

- 첫 실행 시 파일 압축 해제로 인해 약간의 시간이 걸릴 수 있습니다
- Windows Defender나 백신 프로그램이 실행 파일을 차단할 수 있습니다
  - 이 경우 "추가 정보" → "실행"을 클릭하세요
- 실행 파일은 현재 Windows에서만 빌드됩니다
  - Mac/Linux용 빌드는 해당 OS에서 PyInstaller를 실행해야 합니다

## 문제 해결

### 빌드 오류 발생 시

1. **PyInstaller 설치 확인**
   ```bash
   python -m pip install pyinstaller
   ```

2. **모든 의존성 설치 확인**
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **빌드 폴더 정리 후 재시도**
   - `build/`, `dist/`, `__pycache__/` 폴더 삭제
   - `app.spec` 파일 삭제 후 다시 빌드

### 실행 파일이 작동하지 않을 때

- 콘솔 버전(`build_exe_console.py`)으로 빌드하여 오류 메시지 확인
- 실행 파일과 같은 폴더에 `templates/` 폴더와 키워드 파일이 있는지 확인






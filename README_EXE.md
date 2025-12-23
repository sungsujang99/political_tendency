# 정치편향무드등 실행 파일 사용 가이드

Python을 설치하지 않고도 사용할 수 있는 실행 파일(.exe) 버전입니다.

## 실행 파일 만들기

### 1. 필요한 패키지 설치
```bash
python -m pip install -r requirements.txt
```

### 2. 실행 파일 빌드

**방법 A: 배치 파일 사용 (가장 쉬움)**
```bash
build.bat
```

**방법 B: Python 스크립트 직접 실행**
```bash
# 콘솔 창 있는 버전 (디버깅용)
python build_exe_console.py

# 콘솔 창 없는 버전 (일반 사용자용)
python build_exe.py
```

### 3. 빌드 결과
- `dist/정치편향무드등.exe` 파일이 생성됩니다
- 이 파일 하나만 있으면 실행 가능합니다 (모든 필요한 파일이 포함됨)

## 사용자에게 배포

1. `dist/정치편향무드등.exe` 파일을 복사하여 배포
2. 사용자는 더블클릭만 하면 서버가 시작됩니다
3. 브라우저가 자동으로 열리거나, 터미널에 표시된 주소로 접속

## 주의사항

- **첫 실행 시**: 파일 압축 해제로 인해 약간의 시간이 걸릴 수 있습니다
- **Windows Defender 경고**: 실행 파일을 처음 실행할 때 Windows Defender가 경고할 수 있습니다
  - "추가 정보" → "실행" 클릭
  - 또는 실행 파일을 신뢰할 수 있는 출처로 추가
- **방화벽**: 네트워크 접속을 위해 Windows 방화벽 허용이 필요할 수 있습니다

## 문제 해결

### 실행 파일이 작동하지 않을 때
1. 콘솔 버전(`build_exe_console.py`)으로 빌드하여 오류 메시지 확인
2. 실행 파일과 같은 폴더에 필요한 파일이 있는지 확인:
   - `templates/` 폴더
   - `progressive.json` 또는 `progressive.xlsx`
   - `conservative.json` 또는 `conservative.xlsx`

### 빌드 오류 발생 시
1. 모든 의존성이 설치되었는지 확인:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. PyInstaller가 최신 버전인지 확인:
   ```bash
   python -m pip install --upgrade pyinstaller
   ```
3. 빌드 폴더 정리 후 재시도:
   - `build/`, `dist/`, `__pycache__/` 폴더 삭제
   - `app.spec` 파일 삭제

## 기술적 세부사항

- **PyInstaller**: Python 애플리케이션을 실행 파일로 변환
- **단일 파일 모드**: 모든 의존성을 하나의 .exe 파일에 포함
- **자동 경로 처리**: 실행 파일과 스크립트 모드 모두에서 올바른 경로 사용
- **템플릿 포함**: 웹 인터페이스 템플릿이 실행 파일에 포함됨
- **키워드 파일**: 키워드 파일은 실행 파일과 같은 폴더에서 로드/저장






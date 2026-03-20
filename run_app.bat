@echo off
chcp 65001 >nul
TITLE 공장 점유 현황 시뮬레이션 시스템 구동
echo ======================================================
echo   공장 점유 현황 시뮬레이션 시스템을 시작합니다.
echo ======================================================
echo.

echo 1. 기존 실행 프로세스 정리 중...
:: PowerShell을 사용하여 8501 포트를 사용하는 프로세스를 안전하게 찾아 종료합니다.
powershell -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo 2. 필요한 라이브러리 확인 중...
python -m pip install -r requirements.txt >nul 2>&1

echo 3. 시스템 구동 중... (잠시만 기다려주세요)
echo.
echo [안내] 새 창에서 시스템이 실행됩니다. (기존 탭이 아닌 별도 창)
echo.

:: [Senior Logic] 브라우저 자동 실행을 끄고 명령어로 새 창(New Window) 강제 실행
:: 백그라운드에서 스트림릿 실행
start /b python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true

:: 서버 준비 대기
ping -n 3 127.0.0.1 >nul

:: 윈도우 기본 브라우저 중 가장 확실한 Edge/Chrome 새 창 옵션 사용
start msedge --new-window http://127.0.0.1:8501

if %errorlevel% neq 0 (
    echo.
    echo [오류] 시스템 구동 중 에러가 발생했습니다. 
    echo Python 환경 또는 라이브러리 설치 상태를 확인해주세요.
    echo.
    pause
)

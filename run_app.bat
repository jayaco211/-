@echo off
chcp 65001 > nul
echo ==============================================
echo 유튜브 트렌드 분석기 실행 도우미
echo ==============================================
echo.
echo [1/2] 필수 라이브러리를 확인하고 설치합니다...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [오류] 파이썬(Python)이 설치되어 있지 않거나 경로 설정 문제일 수 있습니다.
    echo 구글에 '파이썬 설치'를 검색해서 설치해주세요.
    pause
    exit
)

echo.
echo [2/2] 프로그램을 실행합니다!
echo 잠시 후 브라우저가 자동으로 열립니다...
echo (프로그램을 종료하려면 이 검은 창을 닫으세요)
echo.
streamlit run app.py
pause

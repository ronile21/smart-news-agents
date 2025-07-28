@echo off
set IMAGE_NAME=news-agent
set ARCH=linux/arm64
set TAG=latest
set TAR_FILE=%IMAGE_NAME%-arm.tar

echo Building Docker image for %ARCH%...

IF EXIST %TAR_FILE% (
    echo Removing existing %TAR_FILE%...
    del /f /q %TAR_FILE%
)

docker buildx build ^
  --platform %ARCH% ^
  --tag %IMAGE_NAME%:%TAG% ^
  --load ^
  .



IF ERRORLEVEL 1 (
    echo Docker build failed!
    exit /b 1
)

echo Saving image to %TAR_FILE%...
docker save -o %TAR_FILE% %IMAGE_NAME%:%TAG%

IF EXIST %TAR_FILE% (
    echo Image saved successfully as %TAR_FILE%
) ELSE (
    echo Failed to save image!
)

pause

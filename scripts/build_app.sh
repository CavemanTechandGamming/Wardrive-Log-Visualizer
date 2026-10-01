#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# build_app.sh — versioned PyInstaller builds (Linux / macOS)
#
# Version comes from src/__init__.py (single source of truth).
#
# By default builds a single onefile binary. Set
# WARDRIVE_LOG_VISUALIZER_BUILD_KINDS=both to also build onedir.
#
# Outputs (example):
#   dist/mac-apple-silicon/0.0.4/portable/WardriveLogVisualizer-0.0.4
#   dist/ubuntu/0.0.4/portable/WardriveLogVisualizer-0.0.4
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ICON_PNG="$ROOT/assets/wardrive-log-visualizer-icon.png"
ICON_PNG_256="$ROOT/assets/wardrive-log-visualizer-icon-256.png"
ICON_ICO="$ROOT/assets/WardriveLogVisualizer.ico"

if [[ ! -f "$ICON_PNG" ]]; then
  echo "Icon PNG missing; generating placeholders ..."
  VENV_BOOT="$ROOT/.venv/bin/python"
  if [[ -x "$VENV_BOOT" ]]; then
    "$VENV_BOOT" scripts/make_placeholder_icon.py
  else
    python3 scripts/make_placeholder_icon.py
  fi
fi
if [[ ! -f "$ICON_PNG" ]]; then
  echo "ERROR: Missing icon PNG: $ICON_PNG"
  exit 1
fi

if [[ -n "${WARDRIVE_LOG_VISUALIZER_PLATFORM:-}" ]]; then
  PLATFORM="$WARDRIVE_LOG_VISUALIZER_PLATFORM"
else
  uname_s="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$uname_s" in
    linux*)
      PLATFORM="linux"
      ;;
    darwin*)
      machine="$(uname -m)"
      if [[ "$machine" == "arm64" ]]; then
        PLATFORM="mac-apple-silicon"
      else
        PLATFORM="mac-intel"
      fi
      ;;
    msys*|cygwin*|mingw*)
      PLATFORM="windows"
      ;;
    *)
      echo "ERROR: Unsupported OS: $(uname -s)"
      exit 1
      ;;
  esac
fi

BUILD_KINDS="${WARDRIVE_LOG_VISUALIZER_BUILD_KINDS:-portable}"

echo
echo "=== Wardrive Log Visualizer — PyInstaller build (${PLATFORM}) ==="
echo "Working directory: $ROOT"
echo "Build kinds: ${BUILD_KINDS}"
echo

VENV_PY="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Virtual environment not found. Running setup_env.sh ..."
  bash scripts/setup_env.sh
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: venv python was not created at $VENV_PY"
  exit 1
fi
if ! "$VENV_PY" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "ERROR: PyInstaller is not installed in the virtual environment."
  echo "Run scripts/setup_env.sh first."
  exit 1
fi

VERSION="$("$VENV_PY" scripts/read_version.py)"
APP_NAME="WardriveLogVisualizer-${VERSION}"
echo "App version: ${VERSION}"
echo

COMMON_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name "$APP_NAME"
  --paths=.
  --add-data "${ICON_PNG}:."
  --collect-all customtkinter
  --collect-all tkinterdnd2
  --hidden-import=tkinterdnd2
)
if [[ -f "$ICON_PNG_256" ]]; then
  COMMON_ARGS+=(--add-data "${ICON_PNG_256}:.")
fi
if [[ -f "$ICON_ICO" ]]; then
  COMMON_ARGS+=(--add-data "${ICON_ICO}:.")
fi

build_portable() {
  echo "Building portable (onefile) ..."
  rm -rf "dist/${PLATFORM}/${VERSION}/portable" "build/${PLATFORM}/${VERSION}/portable"
  mkdir -p "dist/${PLATFORM}/${VERSION}/portable" "build/${PLATFORM}/${VERSION}/portable"

  "$VENV_PY" -m PyInstaller "${COMMON_ARGS[@]}" \
    --onefile \
    --distpath "dist/${PLATFORM}/${VERSION}/portable" \
    --workpath "build/${PLATFORM}/${VERSION}/portable" \
    --specpath "build/${PLATFORM}/${VERSION}/portable" \
    src/__main__.py

  echo "  -> dist/${PLATFORM}/${VERSION}/portable/${APP_NAME}"
}

build_installer() {
  echo "Building installer (onedir) ..."
  rm -rf "dist/${PLATFORM}/${VERSION}/installer" "build/${PLATFORM}/${VERSION}/installer"
  mkdir -p "dist/${PLATFORM}/${VERSION}/installer" "build/${PLATFORM}/${VERSION}/installer"

  "$VENV_PY" -m PyInstaller "${COMMON_ARGS[@]}" \
    --onedir \
    --distpath "dist/${PLATFORM}/${VERSION}/installer" \
    --workpath "build/${PLATFORM}/${VERSION}/installer" \
    --specpath "build/${PLATFORM}/${VERSION}/installer" \
    src/__main__.py

  echo "  -> dist/${PLATFORM}/${VERSION}/installer/${APP_NAME}/"
}

case "$BUILD_KINDS" in
  portable)
    build_portable
    ;;
  installer)
    build_installer
    ;;
  both)
    build_portable
    build_installer
    ;;
  *)
    echo "ERROR: WARDRIVE_LOG_VISUALIZER_BUILD_KINDS must be portable, installer, or both (got: ${BUILD_KINDS})"
    exit 1
    ;;
esac

echo
echo "Build complete."
echo

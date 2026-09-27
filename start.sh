#!/usr/bin/env bash

# ==============================================================================
# OmniCampus ERP & SafeTransit: One-Click Dependency Installer & Launcher
# ==============================================================================
# This script automatically detects missing dependencies (Python venv, packages,
# Node modules), installs them if missing, and starts both backend (port 8000)
# and frontend (port 3000) development servers with unified process termination.
# ==============================================================================

set -eo pipefail

# ANSI Color Codes
BOLD="\033[1m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
DIM="\033[2m"
RESET="\033[0m"

# Workspace Paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Helper: Check if a local TCP port is in use using Python (portable, no lsof/nc needed)
check_port() {
  local port=$1
  python3 -c "import socket; s = socket.socket(); s.settimeout(0.3); s.connect(('127.0.0.1', $port)); s.close()" 2>/dev/null
}

clear 2>/dev/null || true
echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════════════════╗"
echo "  ║        OMNICAMPUS ERP & SAFETRANSIT FLEET INTELLIGENCE           ║"
echo "  ║      Multi-Agent Zero-Trust RBAC & Live Telematics Engine         ║"
echo "  ╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ------------------------------------------------------------------------------
# 1. System Prerequisite Checks
# ------------------------------------------------------------------------------
echo -e "${BOLD}[1/4] Checking system prerequisites...${RESET}"

if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Error: python3 is not installed or not in PATH.${RESET}"
  echo "Please install Python 3.10+ and re-run this script."
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ${GREEN}✓${RESET} Python version: ${BOLD}$PYTHON_VERSION${RESET}"

if ! command -v node &>/dev/null; then
  echo -e "${RED}✗ Error: Node.js is not installed or not in PATH.${RESET}"
  echo "Please install Node.js 18+ and re-run this script."
  exit 1
fi

NODE_VERSION=$(node -v)
echo -e "  ${GREEN}✓${RESET} Node.js version: ${BOLD}$NODE_VERSION${RESET}"

if ! command -v npm &>/dev/null; then
  echo -e "${RED}✗ Error: npm is not installed or not in PATH.${RESET}"
  exit 1
fi
echo -e "  ${GREEN}✓${RESET} npm version: ${BOLD}$(npm -v)${RESET}"

# ------------------------------------------------------------------------------
# 2. Python Virtual Environment & Backend Dependencies
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/4] Verifying Python backend environment...${RESET}"

# Detect existing active venv, backend/.venv, or ./venv
VENV_DIR=""
if [ -f "$BACKEND_DIR/.venv/bin/python" ]; then
  VENV_DIR="$BACKEND_DIR/.venv"
elif [ -f "$ROOT_DIR/venv/bin/python" ]; then
  VENV_DIR="$ROOT_DIR/venv"
else
  echo -e "  ${YELLOW}→${RESET} No virtual environment detected. Creating virtualenv at ${BOLD}backend/.venv${RESET}..."
  python3 -m venv "$BACKEND_DIR/.venv"
  VENV_DIR="$BACKEND_DIR/.venv"
fi

PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
echo -e "  ${GREEN}✓${RESET} Using Python environment: ${DIM}$VENV_DIR${RESET}"

# Check if essential packages are installed (note: PyPI pyjwt imports as 'jwt')
NEEDS_INSTALL=false
if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, sqlalchemy, aiosqlite, jwt, bcrypt" &>/dev/null; then
  NEEDS_INSTALL=true
fi

if [ "$NEEDS_INSTALL" = true ]; then
  echo -e "  ${YELLOW}→${RESET} Installing backend dependencies from ${BOLD}backend/requirements.txt${RESET}..."
  "$PIP_BIN" install --quiet --upgrade pip
  "$PIP_BIN" install --quiet -r "$BACKEND_DIR/requirements.txt"
  echo -e "  ${GREEN}✓${RESET} Backend dependencies installed successfully."
else
  echo -e "  ${GREEN}✓${RESET} All backend Python dependencies are satisfied."
fi

# ------------------------------------------------------------------------------
# 3. Node.js & Frontend Dependencies
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/4] Verifying Frontend dependencies...${RESET}"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo -e "  ${YELLOW}→${RESET} Installing frontend npm dependencies (Next.js, Leaflet, Lucide)..."
  (cd "$FRONTEND_DIR" && npm install)
  echo -e "  ${GREEN}✓${RESET} Frontend npm dependencies installed successfully."
else
  echo -e "  ${GREEN}✓${RESET} All frontend npm packages are installed."
fi

# ------------------------------------------------------------------------------
# 4. Service Launch & Process Management
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/4] Starting OmniCampus services...${RESET}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo -e "\n\n${YELLOW}Shutting down OmniCampus ERP services...${RESET}"
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    pkill -P "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    pkill -P "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo -e "${GREEN}✓ All services stopped cleanly.${RESET}"
  exit 0
}

# Trap manual interruptions (Ctrl+C, SIGTERM)
trap cleanup SIGINT SIGTERM

# Check if Backend is already running on port 8000
if check_port 8000; then
  echo -e "  ${YELLOW}ℹ${RESET} Backend port 8000 is already active. Reusing running instance."
else
  echo -e "  ${CYAN}→${RESET} Launching FastAPI backend on ${BOLD}http://127.0.0.1:8000${RESET}..."
  (
    cd "$BACKEND_DIR"
    exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ) > "$ROOT_DIR/.backend.log" 2>&1 &
  BACKEND_PID=$!

  # Wait for backend port to become responsive
  for i in {1..30}; do
    if check_port 8000; then
      break
    fi
    sleep 0.2
  done
  echo -e "  ${GREEN}✓${RESET} Backend API server running (PID: $BACKEND_PID, logs: .backend.log)."
fi

# Check if Frontend is already running on port 3000
if check_port 3000; then
  echo -e "  ${YELLOW}ℹ${RESET} Frontend port 3000 is already active. Reusing running instance."
else
  echo -e "  ${CYAN}→${RESET} Launching Next.js frontend on ${BOLD}http://localhost:3000${RESET}..."
  (
    cd "$FRONTEND_DIR"
    exec npm run dev
  ) > "$ROOT_DIR/.frontend.log" 2>&1 &
  FRONTEND_PID=$!

  # Wait for frontend port to become responsive
  for i in {1..30}; do
    if check_port 3000; then
      break
    fi
    sleep 0.2
  done
  echo -e "  ${GREEN}✓${RESET} Frontend Next.js server running (PID: $FRONTEND_PID, logs: .frontend.log)."
fi

# ------------------------------------------------------------------------------
# System Ready Banner
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}═══════════════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}       🚀 OmniCampus ERP & SafeTransit is LIVE!                     ${RESET}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════════${RESET}"
echo -e ""
echo -e "  ${BOLD}🖥️  Web Application:${RESET}   ${CYAN}http://localhost:3000${RESET}"
echo -e "  ${BOLD}📚 API Swagger Docs:${RESET}   ${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  ${BOLD}⚡ Live Telemetry:${RESET}     ${CYAN}ws://localhost:8000/ws/transit/{bus_id}${RESET}"
echo -e ""
echo -e "${BOLD}🔑 Pre-Configured Demo Accounts (Password: ${GREEN}password123${RESET}${BOLD}):${RESET}"
echo -e "  ${CYAN}• Student:${RESET}  student@campus.edu  (Jane Doe • Section A • Bus 1)"
echo -e "  ${CYAN}• Faculty:${RESET}  faculty@campus.edu  (Prof. Alan Turing • CS HOD • Class Rosters)"
echo -e "  ${CYAN}• Parent:${RESET}   parent@campus.edu   (Robert Doe • Ward: Jane Doe • 500m Geofencing)"
echo -e "  ${CYAN}• Admin:${RESET}    admin@campus.edu    (Sarah Connor • Fleet Governance • Audit Logs)"
echo -e ""
echo -e "${DIM}Press [Ctrl+C] at any time to gracefully terminate both services.${RESET}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════════${RESET}"

# Continuous health monitor loop (keeps script running until user interrupts)
while true; do
  if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "\n${RED}✗ Backend server stopped unexpectedly.${RESET}"
    echo "Check backend log: $ROOT_DIR/.backend.log"
    cleanup
  fi
  if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "\n${RED}✗ Frontend server stopped unexpectedly.${RESET}"
    echo "Check frontend log: $ROOT_DIR/.frontend.log"
    cleanup
  fi
  sleep 1
done

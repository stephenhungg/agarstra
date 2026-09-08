#!/bin/zsh
set -e
cd "$(dirname "$0")/app"
export PATH="/opt/homebrew/bin:$PATH"
npm start

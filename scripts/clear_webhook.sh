#!/usr/bin/env bash
set -euo pipefail
: "${BOT_TOKEN:?Need BOT_TOKEN}"
TG_API="https://api.telegram.org/bot${BOT_TOKEN}"
curl -sS "$TG_API/deleteWebhook?drop_pending_updates=true"
echo

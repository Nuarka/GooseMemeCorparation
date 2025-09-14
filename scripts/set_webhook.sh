#!/usr/bin/env bash
set -euo pipefail
: "${BOT_TOKEN:?Need BOT_TOKEN}"
: "${PUBLIC_URL:?Need PUBLIC_URL}"
TG_API="https://api.telegram.org/bot${BOT_TOKEN}"
curl -sS -X POST "$TG_API/setWebhook" -H 'Content-Type: application/json' -d "{"url":"${PUBLIC_URL}/webhook"}"
echo

#!/bin/bash
# Finanz-Bot Setup Script
# Einfach ausführen: bash setup.sh

set -e

echo "🏦 Finanz-Bot Setup..."

# Python venv
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual Environment erstellt"
fi

source venv/bin/activate
pip install -r requirements.txt --quiet
echo "✅ Dependencies installiert"

# Data Verzeichnis
mkdir -p data
echo "✅ Data-Verzeichnis erstellt"

# .env prüfen
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=DEIN_TOKEN_HIER
TELEGRAM_CHAT_ID=DEINE_CHAT_ID_HIER
EOF
    echo "⚠️  .env erstellt - bitte Token und Chat-ID eintragen!"
    echo "   Token: @BotFather auf Telegram"
    echo "   Chat-ID: @userinfobot auf Telegram"
else
    echo "✅ .env vorhanden"
fi

echo ""
echo "🚀 Setup fertig! Starten mit:"
echo "   source venv/bin/activate"
echo "   python3 main.py"

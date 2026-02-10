#!/bin/bash
echo "🔧 Setting up environment..."
mkdir -p data/raw data/processed log config

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Copying from .env.example..."
    cp .env.example .env
fi

# Install AWS CLI for syncing (if missing)
if ! command -v aws &> /dev/null; then
    echo "📦 AWS CLI not found. Please install it to use syncing features."
    echo "   (sudo apt install awscli)"
fi

echo "✅ Setup complete. Fill in your .env file!"

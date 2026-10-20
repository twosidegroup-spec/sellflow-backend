#!/bin/bash
set -e

# Force Python 3.13 compatibility
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Build requirements
pip install -r requirements.txt

# Run migrations
alembic upgrade head

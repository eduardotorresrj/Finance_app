#!/usr/bin/env python3
"""
WSGI config for Finance App
"""

import os
from app import create_app

# Cria a aplicação Flask
app = create_app()

if __name__ == "__main__":
    app.run()

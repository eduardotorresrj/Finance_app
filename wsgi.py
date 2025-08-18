#!/usr/bin/env python3
"""
WSGI config for Finance App
"""

import os
from app import create_app  # Importa a factory function

app = create_app()  # Cria a instância da aplicação

if __name__ == "__main__":
    app.run()  # Opcional: permite executar com python wsgi.py


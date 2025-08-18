#!/usr/bin/env python3
"""
Script para inicializar o banco de dados com as novas estruturas
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se já existe um usuário
        if not User.query.first():
            # Criar usuário de teste
            user = User(
                username='teste',
                password_hash=generate_password_hash('123456'),
                email='teste@example.com'
            )
            db.session.add(user)
            db.session.commit()
            print("✅ Usuário 'teste' criado com sucesso!")
            print("   Usuário: teste")
            print("   Senha: 123456")
        else:
            print("✅ Banco de dados já inicializado!")

if __name__ == '__main__':
    init_database() 
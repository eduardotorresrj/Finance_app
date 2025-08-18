#!/usr/bin/env python3
"""
Script para reiniciar a aplicação e limpar cache
"""

import os
import sys
import subprocess
import time

def restart_app():
    """Reinicia a aplicação Flask"""
    print("🔄 Reiniciando a aplicação Finance App...")
    
    # Parar processos Python existentes
    try:
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], capture_output=True)
        print("✅ Processos Python anteriores finalizados")
    except:
        pass
    
    # Aguardar um pouco
    time.sleep(2)
    
    # Iniciar a aplicação
    try:
        print("🚀 Iniciando a aplicação...")
        subprocess.Popen([sys.executable, "app.py"], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        print("✅ Aplicação iniciada com sucesso!")
        print("\n📋 INSTRUÇÕES:")
        print("1. Abra seu navegador")
        print("2. Acesse: http://127.0.0.1:5000")
        print("3. Faça login na sua conta")
        print("4. No dashboard, você verá o botão verde 'IA Financeira'")
        print("5. Se não aparecer, pressione Ctrl+F5 para forçar atualização")
        
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")

if __name__ == "__main__":
    restart_app() 
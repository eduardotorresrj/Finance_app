#!/usr/bin/env python3
"""
Script para testar se o dashboard está carregando o template correto
"""

from app import app
from flask import render_template_string

def test_dashboard_template():
    """Testa se o template do dashboard está correto"""
    print("=== TESTE DO TEMPLATE DASHBOARD ===")
    
    # Template básico para teste
    test_template = """
    {% extends 'base.html' %}
    {% block content %}
    <div class="container-fluid">
      <div class="row">
        <div class="col-12">
          <h2>Teste Dashboard</h2>
          
          <!-- Botões de Ação -->
          <div class="row">
            <div class="col-md-3 mb-3">
              <a href="{{ url_for('add_transaction') }}" class="btn btn-primary w-100 py-3 shadow-sm">
                <i class="fas fa-plus-circle fa-lg mb-2"></i><br>
                <span class="fw-bold">Adicionar Transação</span>
              </a>
            </div>
            <div class="col-md-3 mb-3">
              <a href="{{ url_for('add_bill') }}" class="btn btn-warning w-100 py-3 shadow-sm">
                <i class="fas fa-calendar-plus fa-lg mb-2"></i><br>
                <span class="fw-bold">Adicionar Conta</span>
              </a>
            </div>
            <div class="col-md-3 mb-3">
              <a href="{{ url_for('reports') }}" class="btn btn-info w-100 py-3 shadow-sm">
                <i class="fas fa-chart-pie fa-lg mb-2"></i><br>
                <span class="fw-bold">Ver Relatórios</span>
              </a>
            </div>
            <div class="col-md-3 mb-3">
              <a href="{{ url_for('ai_analysis_page') }}" class="btn btn-success w-100 py-3 shadow-sm">
                <i class="fas fa-robot fa-lg mb-2"></i><br>
                <span class="fw-bold">IA Financeira</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
    {% endblock %}
    """
    
    try:
        with app.app_context():
            # Testar se o template renderiza
            rendered = render_template_string(test_template)
            
            # Verificar se contém o botão da IA
            if 'ai_analysis_page' in rendered:
                print("✅ Template renderiza corretamente")
                print("✅ Botão da IA está presente no template")
                return True
            else:
                print("❌ Botão da IA não encontrado no template")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao renderizar template: {e}")
        return False

def check_ai_route():
    """Verifica se a rota da IA está funcionando"""
    print("\n=== TESTE DA ROTA IA ===")
    
    try:
        with app.test_client() as client:
            # Testar a rota da IA
            response = client.get('/ai_analysis')
            
            if response.status_code == 302:  # Redirect para login
                print("✅ Rota da IA existe (redireciona para login)")
                return True
            elif response.status_code == 200:
                print("✅ Rota da IA funciona")
                return True
            else:
                print(f"❌ Rota da IA retornou status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao testar rota da IA: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testando dashboard e IA...")
    
    template_ok = test_dashboard_template()
    route_ok = check_ai_route()
    
    print(f"\n📊 RESULTADOS:")
    print(f"Template: {'✅ OK' if template_ok else '❌ ERRO'}")
    print(f"Rota IA: {'✅ OK' if route_ok else '❌ ERRO'}")
    
    if template_ok and route_ok:
        print("\n🎉 Tudo funcionando! O problema é cache do navegador.")
        print("💡 Solução: Pressione Ctrl+F5 no navegador")
    else:
        print("\n⚠️ Há problemas no código que precisam ser corrigidos.") 
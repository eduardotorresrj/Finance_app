#!/usr/bin/env python3
"""
Script de teste para verificar se a IA Financeira está funcionando
"""

from app import app

def test_routes():
    """Testa se as rotas da IA estão registradas"""
    print("=== TESTE DE ROTAS DA IA FINANCEIRA ===")
    
    # Lista todas as rotas
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append((rule.rule, rule.endpoint))
    
    # Procura pelas rotas da IA
    ai_routes = [route for route in routes if 'ai' in route[1].lower() or 'financial' in route[1].lower()]
    
    print(f"Total de rotas encontradas: {len(routes)}")
    print(f"Rotas da IA encontradas: {len(ai_routes)}")
    
    for route, endpoint in ai_routes:
        print(f"  {route} -> {endpoint}")
    
    # Verifica se as rotas específicas existem
    expected_routes = ['/ai_analysis', '/financial_advisor']
    missing_routes = []
    
    for expected in expected_routes:
        found = False
        for route, endpoint in routes:
            if route == expected:
                found = True
                break
        if not found:
            missing_routes.append(expected)
    
    if missing_routes:
        print(f"\n❌ Rotas faltando: {missing_routes}")
    else:
        print("\n✅ Todas as rotas da IA estão registradas!")
    
    return len(missing_routes) == 0

if __name__ == "__main__":
    test_routes() 
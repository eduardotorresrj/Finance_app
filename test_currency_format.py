#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste de Formatação Monetária
=============================
Verifica se todos os valores monetários estão sendo formatados corretamente
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_currency_format():
    """Testa a função format_currency"""
    
    print("🧪 TESTE DE FORMATAÇÃO MONETÁRIA")
    print("=" * 50)
    
    try:
        # Importar a função format_currency do app
        from app import format_currency
        
        # Testes com diferentes valores
        test_values = [
            0,
            1,
            10,
            100,
            1000,
            10000,
            100000,
            1000000,
            1234.56,
            12345.67,
            123456.78,
            1234567.89,
            0.01,
            0.1,
            1.5,
            2.23,
            500,
            1500,
            2000,
            3000,
            5000,
            10000,
            20000,
            3561.50,
            2275.08
        ]
        
        print("📊 Testando formatação de valores:")
        print("-" * 40)
        
        for value in test_values:
            formatted = format_currency(value)
            print(f"• {value:>10} → {formatted}")
        
        print("\n✅ Teste de formatação monetária concluído!")
        
        # Verificar se a formatação está correta (padrão brasileiro)
        test_cases = [
            (1000, "R$ 1.000,00"),
            (1234.56, "R$ 1.234,56"),
            (1000000, "R$ 1.000.000,00"),
            (0, "R$ 0,00"),
            (0.01, "R$ 0,01")
        ]
        
        print("\n🔍 Verificando padrão brasileiro:")
        print("-" * 40)
        
        all_correct = True
        for value, expected in test_cases:
            result = format_currency(value)
            status = "✅" if result == expected else "❌"
            print(f"{status} {value:>10} → {result:>15} (esperado: {expected})")
            if result != expected:
                all_correct = False
        
        if all_correct:
            print("\n🎉 TODOS OS TESTES PASSARAM!")
            print("✅ Formatação monetária está correta!")
        else:
            print("\n⚠️ ALGUNS TESTES FALHARAM!")
            print("❌ Formatação monetária precisa ser corrigida!")
            
    except ImportError as e:
        print(f"❌ Erro ao importar: {e}")
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_currency_format() 
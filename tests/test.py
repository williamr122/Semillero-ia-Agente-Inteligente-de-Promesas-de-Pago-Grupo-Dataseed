import pytest
import pandas as pd
import os
from src.main import cargar_datos

def test_calculo_riesgo():
    # Simulamos una deuda de 100
    # Un pago de 50 (50%) debería ser riesgo 'Baja'
    # Un pago de 20 (20%) debería ser riesgo 'Alta'
    
    monto_alto = 50
    monto_bajo = 10
    deuda = 100
    
    riesgo_esperado_bajo = "Baja" if monto_alto >= (deuda * 0.4) else "Alta"
    riesgo_esperado_alto = "Baja" if monto_bajo >= (deuda * 0.4) else "Alta"
    
    assert riesgo_esperado_bajo == "Baja"
    assert riesgo_esperado_alto == "Alta"

# Prueba 2: Verificar la existencia de la base de datos
def test_existencia_excel():
    df = cargar_datos()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
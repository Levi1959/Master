from machine import ADC, Pin
import time

# VSYS monitorado no ADC3 (GPIO29)
adc_vsys = ADC(29)

# 3V3 monitorado no ADC0 (GPIO26)
# 👉 Precisa ligar fisicamente o pino 3V3 ao GP26
adc_3v3 = ADC(26)

def ler_vsys():
    valor = adc_vsys.read_u16()
    # Conversão: leitura * (3.3 / 65535) * 3
    tensao = (valor / 65535) * 3.3 * 3
    return tensao

def ler_3v3():
    valor = adc_3v3.read_u16()
    tensao = (valor / 65535) * 3.3
    return tensao

while True:
    vsys = ler_vsys()
    v3v3 = ler_3v3()
    
    # Detecção automática da fonte
    if vsys > 4.5:  
        fonte = "Porta USB"
    elif 3.0 < vsys < 4.5:
        fonte = "Bateria/Fonte externa"
    else:
        fonte = "Desconhecida / abaixo do normal"
    
    # Exibe resultados no Thonny
    print("Tensão de Entrada (VSYS) = {:.2f} V".format(vsys))
    print("Tensão Regulada (3V3)    = {:.2f} V".format(v3v3))
    print("Fonte detectada: {}".format(fonte))
    print("-" * 40)
    
    time.sleep(1)

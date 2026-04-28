import network
import time
import machine
from umqtt.simple import MQTTClient
import json
import ntptime
import binascii

from machine import Pin, I2C, WDT
import ssd1306
import dht

# ==================== Configuração de Fuso Horário ====================
# UTC de Brasília (UTC-3). O deslocamento é em segundos.
# -3 horas * 60 minutos/hora * 60 segundos/minuto = -10800 segundos.
UTC_OFFSET_BRAZIL = -3 * 3600

# ==================== Configuração de Periféricos ====================
# Configuração do Watchdog (máximo de 8000 ms)
# O WDT precisa ser alimentado frequentemente para não reiniciar a placa.
wdt = WDT(timeout=8000)

# Configuração I2C do OLED
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Configuração do DHT22
sensor = dht.DHT22(Pin(2))

# Configuração do botão
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER = "163.176.182.91"
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_PUB_ALL = b"Urbano_Temperatura_Local"

# ==================== Funções de Conexão ====================
def conecta_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    
    wlan.config(hostname=hostname_placa)
    print(f"Tentando conectar com o nome de host: {hostname_placa}")
    
    oled.fill(0)
    oled.text("Conectando Wi-Fi", 0, 0)
    oled.show()
    
    wlan.connect(SSID, PASSWORD)
    
    # Aguarda a conexão Wi-Fi. Alimenta o WDT a cada segundo.
    max_tentativas_wifi = 90
    tentativas_wifi = 0
    while not wlan.isconnected() and tentativas_wifi < max_tentativas_wifi:
        wdt.feed() # Alimenta o WDT para evitar timeout durante a espera
        time.sleep(1)
        tentativas_wifi += 1
    
    if not wlan.isconnected():
        print("Falha na conexão Wi-Fi.")
        return None, None

    print("Conectado ao Wi-Fi:", wlan.ifconfig())
    
    try:
        ntptime.host = "a.ntp.br"
        ntptime.settime()
        # --- INÍCIO DA CORREÇÃO DE FUSO HORÁRIO ---
        # time.time() retorna os segundos desde a época UTC.
        # Aplicamos o deslocamento UTC-3 para ajustar para Brasília.
        segundos_brasilia = time.time() + UTC_OFFSET_BRAZIL
        # Define a hora do RTC interno com o novo valor ajustado.
        # O time.mktime() converte a tupla (ano, mês, dia, hora, min, seg, dia_semana, dia_ano)
        # para segundos desde a época. Como a função time.localtime() de micropython
        # já considera a hora interna do RTC, usamos time.localtime() e, em seguida, time.time()
        # para obter os segundos ajustados.
        # Uma maneira mais direta em micropython é simplesmente definir a hora.
        # No entanto, time.localtime() *lê* o RTC, então vamos reajustar o RTC.
        # time.time() retorna a hora atual do RTC em segundos desde a época.
        # O módulo 'time' de micropython permite redefinir a hora da seguinte forma:
        time.localtime(segundos_brasilia) # Isso não define o RTC, mas retorna a tupla.
        # Para *definir* o RTC, é necessário fazer o seguinte (se disponível na sua build):
        # time.set_time(time.gmtime(segundos_brasilia))
        # No entanto, a forma mais comum e robusta é:
        # 1. Obter a hora UTC do NTP (feito por ntptime.settime())
        # 2. Em seguida, usar time.localtime() no código principal, que retorna o UTC.
        # 3. Para *mostrar* Brasília, calculamos o deslocamento em tempo real a cada leitura.
        # Vamos reverter a alteração do RTC e apenas calcular o deslocamento na leitura para ser mais seguro.
        # Apenas redefinir a hora com time.set_time() não está universalmente disponível.

        # Alternativa mais robusta: vamos apenas garantir que a sincronização ocorreu
        # e aplicar o offset no loop principal.
        print("Data e hora sincronizadas via NTP (UTC).")
    except Exception as e:
        print("Erro ao sincronizar NTP:", e)

    return wlan, hostname_placa

def conecta_mqtt(client_id):
    client = MQTTClient(client_id, MQTT_SERVER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
    client.connect()
    oled.fill(0)
    oled.text("MQTT conectado", 0, 0)
    oled.show()
    print("Conectado ao broker MQTT")
    return client

# ==================== Funções para o DHT e OLED ====================
def mostrar_dados(leitura_num, temp, hum):
    oled.fill(0)
    oled.text("Leitura #{}".format(leitura_num), 0, 0)
    oled.text("Temp: {:.1f} C".format(temp), 0, 20)
    oled.text("Umid: {:.1f} %".format(hum), 0, 40)
    oled.show()

# ==================== Programa Principal ====================
leitura_numero = 0

try:
    # Primeira tentativa de conexão ao iniciar
    wlan, hostname_placa = conecta_wifi()
    if wlan is None:
        print("Falha na primeira conexão Wi-Fi, reiniciando...")
        oled.text("Erro Wi-Fi!", 0, 0)
        oled.show()
        time.sleep(5)
        machine.reset()
    
    client = conecta_mqtt(hostname_placa)

    while True:
        wdt.feed()
        leitura_numero += 1
        
        # --- Verificação de robustez: Garante que o Wi-Fi está ativo ---
        if not wlan.isconnected():
            print("Conexão Wi-Fi perdida. Tentando reconectar...")
            try:
                wlan, hostname_placa = conecta_wifi()
                if wlan:
                    client = conecta_mqtt(hostname_placa)
                else:
                    print("Falha na reconexão Wi-Fi, reiniciando...")
                    machine.reset()
            except Exception as e:
                print("Falha na reconexão completa. Reiniciando...")
                machine.reset()
        # --- Fim da verificação de robustez ---

        try:
            time.sleep(2)
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            
            mostrar_dados(leitura_numero, temp, hum)

            print("=== Leitura #{} ===".format(leitura_numero))
            print("Temperatura: {:.1f} C, Umidade: {:.1f} %".format(temp, hum))
            print("Servidor: {}".format(MQTT_SERVER))
            
            # Obter o horário atual em segundos (UTC)
            segundos_utc = time.time()
            # Aplicar o deslocamento para obter os segundos de Brasília
            segundos_brasilia = segundos_utc + UTC_OFFSET_BRAZIL
            # Converter os segundos de Brasília para a tupla de tempo (localtime)
            agora_brasilia = time.localtime(segundos_brasilia)
            horario_formatado = "{:02d}:{:02d}:{:02d}".format(agora_brasilia[3], agora_brasilia[4], agora_brasilia[5])
            
            # Cria uma string de texto simples com todas as informações
            msg = "[{}] Leitura #{} | Temp: {:.1f} C | Umid: {:.1f} % | Host: {}".format(
                horario_formatado, leitura_numero, temp, hum, hostname_placa
            )
            
            # Lógica de publicação com tentativas
            tentativas_pub = 0
            publicado_sucesso = False
            while tentativas_pub < 3 and not publicado_sucesso:
                try:
                    client.publish(TOPIC_PUB_ALL, msg.encode())
                    print("Publicado com sucesso: " + msg)
                    publicado_sucesso = True
                except Exception as e:
                    print("Erro de publicação, tentando reconectar... Tentativa {}".format(tentativas_pub + 1))
                    oled.fill(0)
                    oled.text("Erro Pub!", 0, 20)
                    oled.show()
                    time.sleep(5)
                    try:
                        client.disconnect()
                        client = conecta_mqtt(hostname_placa)
                    except Exception as e_recon:
                        print("Erro na reconexão:", e_recon)
                    tentativas_pub += 1
            
            if not publicado_sucesso:
                print("Falha na publicação após 3 tentativas. Reiniciando...")
                oled.fill(0)
                oled.text("Falha!", 0, 20)
                oled.show()
                time.sleep(5)
                machine.reset()

        except OSError as e:
            oled.fill(0)
            oled.text("Erro sensor", 0, 20)
            oled.show()
            print("Erro de leitura do sensor:", e)
        
        print("Iniciando espera de 20 segundos...")
        for _ in range(20):
            wdt.feed() # Mantém o WDT alimentado durante a espera
            if botao.value():
                # Código para lidar com o botão, se necessário.
                pass
            time.sleep(1)
            
except Exception as e:
    oled.fill(0)
    oled.text("ERRO CRITICO", 0, 20)
    oled.text(str(e), 0, 40)
    oled.show()
    print("Erro critico:", e)
    machine.reset()
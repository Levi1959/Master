import network
import time
import machine
import binascii
from umqtt.simple import MQTTClient
import ntptime
from machine import Pin, I2C
import ssd1306
import dht

# ==================== DELAY DE SINCRONISMO ====================
# Espera 30 segundos antes de ligar o Wi-Fi para não colidir com a outra placa
print("Aguardando 30 segundos para sincronismo de rede...")
time.sleep(30)

# ==================== Configuração de Periféricos ====================
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except:
    oled = None

sensor = dht.DHT22(Pin(2))

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER_NUVEM = "163.176.182.91"
MQTT_SERVER_LOCAL = "192.168.15.14"
TOPIC_PUB_NUVEM = b"Urbano_Temperatura"
TOPIC_PUB_LOCAL = b"Urbano_Temperatura_Local"
FUSO_HORARIO_SEGUNDOS = -3 * 3600

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac_address = binascii.hexlify(wlan.config('mac')).decode()

# Prefixo ÚNICO para esta placa: P_REM_
hostname_placa = "P_REM_" + mac_address[-6:]

# ==================== Funções de Apoio ====================

def conectar_wifi():
    if not wlan.isconnected():
        print(f"Conectando Wi-Fi como {hostname_placa}...")
        wlan.connect(SSID, PASSWORD)
        for _ in range(20):
            if wlan.isconnected(): return True
            time.sleep(1)
    return wlan.isconnected()

def publicar_dados(msg):
    """Conecta, envia e desconecta imediatamente."""
    # Enviar para Nuvem
    try:
        c_nuvem = MQTTClient(hostname_placa, MQTT_SERVER_NUVEM, user="icts", password="icts", keepalive=60)
        c_nuvem.connect()
        c_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
        c_nuvem.disconnect()
        print("Enviado para Nuvem.")
    except:
        print("Erro na Nuvem.")

    # Enviar para Local
    try:
        c_local = MQTTClient(hostname_placa, MQTT_SERVER_LOCAL, user="icts", password="icts", keepalive=60)
        c_local.connect()
        c_local.publish(TOPIC_PUB_LOCAL, msg.encode())
        c_local.disconnect()
        print("Enviado para Local.")
    except:
        print("Erro no Local.")

# ==================== Loop Principal ====================
leitura_numero = 0

while True:
    try:
        if conectar_wifi():
            leitura_numero += 1
            print(f"\n--- LEITURA REMOTA #{leitura_numero} ---")

            # Sincroniza hora apenas na leitura #1
            if leitura_numero == 1:
                try: 
                    ntptime.host = "a.ntp.br"
                    ntptime.settime()
                except: pass

            sensor.measure()
            t, h = sensor.temperature(), sensor.humidity()
            
            t_tuple = time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)
            horario_str = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t_tuple[:6])
            
            payload = f"{leitura_numero},{horario_str},{t:.1f},{h:.1f},{hostname_placa}"
            print(f"Payload: {payload}")

            publicar_dados(payload)

            # --- LÓGICA DO OLED (IDÊNTICA AO COM SD) ---
            if oled:
                oled.fill(0)
                oled.text("ESTACAO REMOTA", 10, 0)
                oled.text(f"L:{leitura_numero} {horario_str[11:16]}", 0, 15)
                oled.text(f"T: {t:.1f} C", 0, 35)
                oled.text(f"U: {h:.1f} %", 0, 50)
                oled.show()
                time.sleep(60)

                for min_restante in range(9, 0, -1):
                    oled.fill(0)
                    oled.text("AGUARDANDO", 25, 0)
                    oled.text(f"Prox. leitura em", 5, 25)
                    oled.text(f"{min_restante} minutos", 25, 45)
                    oled.show()
                    time.sleep(60)
            else:
                time.sleep(540)

    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(10)
        machine.reset()
import network
import time
import machine
import binascii
import rp2
from umqtt.simple import MQTTClient
import ntptime
from machine import Pin, I2C
import ssd1306
import dht

# Libera os canais Wi-Fi do Brasil
rp2.country('BR')

# ==================== DELAY DE SINCRONISMO ====================
print("Aguardando 30 segundos para sincronismo de rede...")
time.sleep(30)

# ==================== Configuração de Periféricos ====================
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except Exception as e:
    print("Erro OLED:", e)
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

hostname_placa = "P_REM_" + mac_address[-6:]

# ==================== Funções de Apoio ====================

def conectar_wifi():
    if not wlan.isconnected():
        print(f"Conectando Wi-Fi como {hostname_placa}...")
        wlan.connect(SSID, PASSWORD)
        for _ in range(20):
            if wlan.isconnected(): 
                print("Wi-Fi Conectado! IP:", wlan.ifconfig()[0])
                return True
            time.sleep(1)
        print("Falha ao conectar no Wi-Fi. Status:", wlan.status())
    return wlan.isconnected()

def publicar_dados(msg):
    # LIGA O OLED ANTES DE TENTAR ENVIAR PARA PROVAR QUE ELE FUNCIONA
    if oled:
        oled.fill(0)
        oled.text("ENVIANDO MQTT...", 0, 0)
        oled.text("Aguarde...", 0, 20)
        oled.show()

    try:
         print(" -> [1/4] Preparando cliente Nuvem...")
         c_nuvem = MQTTClient(hostname_placa, MQTT_SERVER_NUVEM, user="icts", password="icts", keepalive=60)
         print(" -> [2/4] Conectando na Nuvem (Isso pode travar)...")
         c_nuvem.connect()
         print(" -> [3/4] Conectado! Publicando na Nuvem...")
         c_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
         c_nuvem.disconnect()
         print(" -> [4/4] [OK] Nuvem concluida.")
     except Exception as e:
         print(f" [ERRO] Falha na Nuvem: {e}")

    # Enviar para Local
    try:
        print(" -> [1/4] Preparando cliente Local...")
        c_local = MQTTClient(hostname_placa, MQTT_SERVER_LOCAL, user="icts", password="icts", keepalive=60)
        print(" -> [2/4] Conectando no Local (Isso pode travar)...")
        c_local.connect()
        print(" -> [3/4] Conectado! Publicando no Local...")
        c_local.publish(TOPIC_PUB_LOCAL, msg.encode())
        c_local.disconnect()
        print(" -> [4/4] [OK] Local concluido.")
    except Exception as e:
        print(f" [ERRO] Falha no Local: {e}")

# ==================== Loop Principal ====================
leitura_numero = 0

while True:
    try:
        if conectar_wifi():
            leitura_numero += 1
            print(f"\n--- LEITURA REMOTA #{leitura_numero} ---")

            if leitura_numero == 1:
                try: 
                    ntptime.host = "a.ntp.br"
                    ntptime.settime()
                except Exception as e: 
                    print("Erro NTP:", e)

            sensor.measure()
            t, h = sensor.temperature(), sensor.humidity()
            
            t_tuple = time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)
            horario_str = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t_tuple[:6])
            
            payload = f"{leitura_numero},{horario_str},{t:.1f},{h:.1f},{hostname_placa}"
            print(f"Payload: {payload}")

            # CHAMA A FUNÇÃO DE PUBLICAR (ONDE ESTÁ O NOSSO TESTE)
            publicar_dados(payload)

            # SÓ CHEGA AQUI SE O MQTT NÃO TRAVAR A PLACA
            if oled:
                oled.fill(0)
                oled.text("ESTACAO REMOTA", 10, 0)
                oled.text(f"L:{leitura_numero} {horario_str[11:16]}", 0, 15)
                oled.text(f"T: {t:.1f} C", 0, 35)
                oled.text(f"U: {h:.1f} %", 0, 50)
                oled.show()
                time.sleep(60) # Espera 1 minuto mostrando os dados

                # Contagem regressiva do segundo minuto
                for min_restante in range(1, 0, -1):
                    oled.fill(0)
                    oled.text("AGUARDANDO", 25, 0)
                    oled.text(f"Prox. leitura em", 5, 25)
                    oled.text(f"{min_restante} minutos", 25, 45)
                    oled.show()
                    time.sleep(60)
            else:
                print("Aguardando 2 minutos (sem OLED)...")
                time.sleep(120)

    except Exception as e:
        print(f"Erro no loop (sensor ou rede): {e}")
        # machine.reset() # <--- Comentado propositalmente
        time.sleep(5)
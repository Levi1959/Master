import network
import time
import machine
import os
import binascii
from umqtt.simple import MQTTClient
import ntptime
from machine import Pin, I2C, SPI
import ssd1306
import dht
import sdcard

# ==================== Configuração de Periféricos ====================
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except:
    oled = None

sensor = dht.DHT22(Pin(2))

# Configuração SD Card
try:
    spi = SPI(0, baudrate=2000000, miso=Pin(16), sck=Pin(18), mosi=Pin(19))
    sd = sdcard.SDCard(spi, Pin(17, Pin.OUT))
    os.mount(sd, "/sd")
    print("SD Card Montado.")
except:
    sd = None
    print("Falha no SD Card.")

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
hostname_placa = "SD_CARD_" + mac_address[-6:]

# ==================== Funções de Apoio ====================

def conectar_wifi():
    if not wlan.isconnected():
        print("Conectando Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        for _ in range(20):
            if wlan.isconnected(): return True
            time.sleep(1)
    return wlan.isconnected()

def publicar_dados(msg):
    for server in [MQTT_SERVER_NUVEM, MQTT_SERVER_LOCAL]:
        topic = TOPIC_PUB_NUVEM if server == MQTT_SERVER_NUVEM else TOPIC_PUB_LOCAL
        try:
            c = MQTTClient(hostname_placa, server, user="icts", password="icts", keepalive=60)
            c.connect()
            c.publish(topic, msg.encode())
            c.disconnect()
            print(f"Enviado para {server}")
        except:
            print(f"Erro ao enviar para {server}")

# ==================== Loop Principal ====================
leitura_numero = 0

while True:
    try:
        if conectar_wifi():
            leitura_numero += 1
            print(f"\n--- LEITURA #{leitura_numero} ---")

            # --- CORREÇÃO DE DATA/HORA ---
            # Verifica se o ano é anterior a 2024 (relógio resetado)
            if time.localtime()[0] < 2024:
                print("Relógio desatualizado. Sincronizando com NTP...")
                try:
                    ntptime.host = "a.st1.ntp.br" # Servidor NTP Brasil
                    ntptime.settime()
                    print("Relógio atualizado com sucesso!")
                except Exception as e:
                    print(f"Falha na sincronização NTP: {e}")

            # Medição
            sensor.measure()
            t, h = sensor.temperature(), sensor.humidity()
            
            # Cálculo do horário com fuso
            t_tuple = time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)
            horario_str = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t_tuple[:6])
            
            payload = f"{leitura_numero},{horario_str},{t:.1f},{h:.1f},{hostname_placa}"
            print(f"Dados: {payload}")
            
            # SD Card
            if sd:
                try:
                    with open(f"/sd/LOG_{t_tuple[2]:02}.csv", "a") as f:
                        f.write(payload + "\n")
                except: print("Erro ao gravar no SD")

            # Publicação MQTT
            publicar_dados(payload)

            # --- LÓGICA DO OLED ---
            if oled:
                # 1. Mostra resultados por 1 minuto
                oled.fill(0)
                oled.text(f"L:{leitura_numero} {horario_str[11:16]}", 0, 0)
                oled.text(f"Temp: {t:.1f} C", 0, 20)
                oled.text(f"Umid: {h:.1f} %", 0, 35)
                oled.text(f"ID:{hostname_placa[-6:]}", 0, 50)
                oled.show()
                time.sleep(60)

                # 2. Contagem regressiva de 9 a 1 minuto
                for min_restante in range(9, 0, -1):
                    oled.fill(0)
                    oled.text("MODO ESPERA", 20, 0)
                    oled.text(f"Proxima leitura", 5, 25)
                    oled.text(f"em: {min_restante} min", 25, 45)
                    oled.show()
                    print(f"Aguardando... {min_restante} min")
                    time.sleep(60)
            else:
                time.sleep(540)

    except Exception as e:
        print(f"Erro detectado: {e}")
        time.sleep(10)
        machine.reset()	
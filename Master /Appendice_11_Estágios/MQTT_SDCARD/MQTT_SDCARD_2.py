import network
import time
import machine
import os
import binascii
from umqtt.simple import MQTTClient
import ntptime
import json
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
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# Configuração SD Card
SD_SCK, SD_MISO, SD_MOSI, SD_CS = 18, 16, 19, 17
SD_MOUNT_POINT = "/sd"
sd = None 
LOG_FILE = ""

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER_NUVEM = "163.176.182.91"
MQTT_SERVER_LOCAL = "192.168.15.14"
TOPIC_PUB_NUVEM = b"Urbano_Temperatura"
TOPIC_PUB_LOCAL = b"Urbano_Temperatura_Local"
FUSO_HORARIO_SEGUNDOS = -3 * 3600

# Variáveis de Estado
hostname_placa = ""
client_nuvem = None
client_local = None
wlan = None
leitura_numero = 0

# ==================== Funções de Tempo e Sincronismo ====================

def sincroniza_horario():
    """Tenta sincronizar o NTP e verifica se a data é válida (> 2023)."""
    max_tentativas = 5
    for i in range(max_tentativas):
        try:
            print(f"Tentativa NTP {i+1}/{max_tentativas}...")
            if oled:
                oled.fill(0)
                oled.text("Sincronizando...", 0, 0)
                oled.text(f"Try {i+1}/{max_tentativas}", 0, 20)
                oled.show()
                
            ntptime.settime() # Busca hora UTC 0
            
            # Verifica se o ano atualizado é coerente (maior que 2023)
            ano_atual = time.localtime()[0]
            if ano_atual > 2023:
                print(f"Relógio sincronizado! Ano: {ano_atual}")
                return True
            else:
                print("Data inválida recebida (Epoch 2020).")
        except Exception as e:
            print(f"Erro NTP: {e}")
        
        time.sleep(2) # Espera antes de tentar de novo
    return False

def obter_horario_rtc(ajustado=True):
    t = time.localtime(time.time() + (FUSO_HORARIO_SEGUNDOS if ajustado else 0))
    # Retorna string formatada e a tupla completa
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t[:6]), t

# ==================== Outras Funções Auxiliares ====================

def conecta_wifi_e_mqtt():
    global hostname_placa, wlan, client_nuvem, client_local
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac = binascii.hexlify(wlan.config('mac')).decode()
    hostname_placa = "Pico W_" + mac[-6:]
    wlan.config(hostname=hostname_placa)
    wlan.connect(SSID, PASSWORD)
    
    # Aguarda conexão
    for _ in range(30):
        if wlan.isconnected(): break
        time.sleep(1)
    
    if not wlan.isconnected(): return False

    # FORÇA SINCRONIZAÇÃO APÓS WIFI CONECTAR
    sincroniza_horario()

    # MQTT
    try:
        client_nuvem = MQTTClient(hostname_placa, MQTT_SERVER_NUVEM, user="icts", password="icts")
        client_nuvem.connect()
        client_local = MQTTClient(hostname_placa, MQTT_SERVER_LOCAL, user="icts", password="icts")
        client_local.connect()
    except: pass
    return True

def inicializa_sd_card(dt_tuple):
    global sd, LOG_FILE
    ano, mes, dia = dt_tuple[0], dt_tuple[1], dt_tuple[2]
    LOG_FILE = "log_{:02}_{:02}_{:04}.csv".format(dia, mes, ano)
    try:
        spi = SPI(0, baudrate=2000000, miso=Pin(SD_MISO), sck=Pin(SD_SCK), mosi=Pin(SD_MOSI))
        sd_instancia = sdcard.SDCard(spi, Pin(SD_CS, Pin.OUT))
        os.mount(sd_instancia, SD_MOUNT_POINT)
        sd = sd_instancia
        return True
    except: return False

def mostrar_dados(leitura_num, temp, hum, horario):
    if oled:
        oled.fill(0)
        oled.text(f"L{leitura_num} {horario[11:16]}", 0, 0)
        oled.text(horario[0:10], 0, 15)
        oled.text(f"T: {temp:.1f} C", 0, 35)
        oled.text(f"U: {hum:.1f} %", 0, 50)
        oled.show()

# ==================== Programa Principal ====================

try:
    if not conecta_wifi_e_mqtt():
        if oled: oled.text("WiFi Fail!", 0, 0); oled.show()
    
    horario_str, dt_tuple = obter_horario_rtc()
    
    # Inicializa SD com a data corrigida
    if not inicializa_sd_card(dt_tuple):
        print("Erro SD")

    while True:
        leitura_numero += 1
        
        # Garante que o WiFi está vivo e a hora está OK
        if wlan and not wlan.isconnected():
            wlan.connect(SSID, PASSWORD)
            time.sleep(5)
            if wlan.isconnected(): sincroniza_horario()

        try:
            sensor.measure()
            temp, hum = sensor.temperature(), sensor.humidity()
            horario_str, _ = obter_horario_rtc()
            
            # Mensagem para MQTT e Log
            msg = f"{leitura_numero},{horario_str},{temp:.1f},{hum:.1f},{hostname_placa}"
            
            # Gravação SD
            if sd:
                with open(f"{SD_MOUNT_POINT}/{LOG_FILE}", "a") as f:
                    f.write(msg + "\n")

            # Publicação MQTT
            try: client_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
            except: pass
            try: client_local.publish(TOPIC_PUB_LOCAL, msg.encode())
            except: pass

            # Ciclo Inteligente do Display (10 minutos)
            tempo_espera = 600
            inicio = time.time()
            while (time.time() - inicio) < tempo_espera:
                # 30 Segundos Ligado
                mostrar_dados(leitura_numero, temp, hum, horario_str)
                for _ in range(30):
                    if (time.time() - inicio) >= tempo_espera: break
                    time.sleep(1)
                
                # 10 Segundos Desligado
                if oled: oled.fill(0); oled.show()
                for _ in range(10):
                    if (time.time() - inicio) >= tempo_espera: break
                    time.sleep(1)

        except Exception as e:
            print("Erro:", e)
            time.sleep(5)

except Exception as e:
    print("Erro Fatal:", e)
    machine.reset()
    
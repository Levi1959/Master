import network
import time
import machine
import binascii
from umqtt.simple import MQTTClient
import ntptime
from machine import Pin, I2C
import ssd1306
import dht

# ==================== Configuração de Periféricos ====================
try:
    # I2C nos pinos 0 (SDA) e 1 (SCL)
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except:
    oled = None
    print("OLED não detectado.")

# DHT22 no pino 2
sensor = dht.DHT22(Pin(2))

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
    """Tenta sincronizar o NTP e verifica se a data é válida."""
    max_tentativas = 5
    for i in range(max_tentativas):
        try:
            print(f"Sincronizando hora ({i+1}/5)...")
            ntptime.settime() 
            if time.localtime()[0] > 2023:
                print("Relógio OK!")
                return True
        except:
            pass
        time.sleep(2)
    return False

def obter_horario_rtc():
    """Retorna o horário formatado (Brasília)."""
    t = time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t[:6])

# ==================== Conectividade ====================

def conecta_tudo():
    global hostname_placa, wlan, client_nuvem, client_local
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Gera hostname baseado no MAC
    mac = binascii.hexlify(wlan.config('mac')).decode()
    hostname_placa = "Pico_Remoto_" + mac[-6:]
    wlan.config(hostname=hostname_placa)
    
    print(f"Conectando Wi-Fi como: {hostname_placa}")
    wlan.connect(SSID, PASSWORD)
    
    for _ in range(30):
        if wlan.isconnected(): break
        time.sleep(1)
    
    if wlan.isconnected():
        sincroniza_horario()
        # Conexão Brokers
        try:
            client_nuvem = MQTTClient(hostname_placa, MQTT_SERVER_NUVEM, user="icts", password="icts")
            client_nuvem.connect()
            print("Conectado Nuvem")
        except: print("Falha Broker Nuvem")
            
        try:
            client_local = MQTTClient(hostname_placa, MQTT_SERVER_LOCAL, user="icts", password="icts")
            client_local.connect()
            print("Conectado Local")
        except: print("Falha Broker Local")
        return True
    return False

def mostrar_dados(leitura_num, temp, hum, horario):
    if oled:
        oled.fill(0)
        oled.text(f"L{leitura_num} {horario[11:16]}", 0, 0)
        oled.text(horario[0:10], 0, 15)
        oled.text(f"T: {temp:.1f} C", 0, 35)
        oled.text(f"U: {hum:.1f} %", 0, 50)
        oled.show()

# ==================== Loop Principal ====================

try:
    conecta_tudo()

    while True:
        leitura_numero += 1
        
        # Monitor de conexão
        if not wlan.isconnected():
            conecta_tudo()

        try:
            sensor.measure()
            temp, hum = sensor.temperature(), sensor.humidity()
            horario_str = obter_horario_rtc()
            
            # Formata mensagem
            msg = f"{leitura_numero},{horario_str},{temp:.1f},{hum:.1f},{hostname_placa}"
            print(f"Enviando: {msg}")

            # Publicação MQTT Nuvem
            try:
                client_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
            except:
                # Tenta reconectar se falhar
                try: client_nuvem.connect()
                except: pass

            # Publicação MQTT Local
            try:
                client_local.publish(TOPIC_PUB_LOCAL, msg.encode())
            except:
                try: client_local.connect()
                except: pass

            # Ciclo Inteligente do Display (Espera de 10 minutos / 600s)
            # Mantém o OLED ligado por 30s e desligado por 10s para não queimar
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
            print("Erro no ciclo:", e)
            time.sleep(10)

except Exception as e:
    print("Erro Crítico:", e)
    time.sleep(5)
    machine.reset()
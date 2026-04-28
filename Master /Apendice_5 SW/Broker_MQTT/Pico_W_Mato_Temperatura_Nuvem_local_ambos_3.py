import network
import time
import machine
from umqtt.simple import MQTTClient
import ntptime
import binascii
from machine import Pin, I2C
import ssd1306
import dht

# ==================== Configuração de Periféricos ====================
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
except Exception as e:
    print(f"Erro OLED: {e}")
    oled = None

sensor = dht.DHT22(Pin(2))
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER_NUVEM = "163.176.182.91"
MQTT_SERVER_LOCAL = "192.168.15.14"
TOPIC_PUB_NUVEM = b"Urbano_Temperatura"
TOPIC_PUB_LOCAL = b"Urbano_Temperatura_Local"
FUSO_HORARIO_SEGUNDOS = -3 * 3600

# ==================== Funções Auxiliares ====================
def show_oled_msg(text1, text2=""):
    if oled:
        oled.fill(0)
        oled.text(text1, 0, 0)
        oled.text(text2, 0, 20)
        oled.show()

def conecta_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac_hex = binascii.hexlify(wlan.config('mac')).decode()
    hostname = "Pico W_" + mac_hex[-6:]
    wlan.config(hostname=hostname)
    
    wlan.connect(SSID, PASSWORD)
    show_oled_msg("Conectando Wi-Fi", hostname)
    
    for _ in range(30):
        if wlan.isconnected(): break
        time.sleep(1)
    
    if wlan.isconnected():
        try:
            ntptime.host = "a.ntp.br"
            ntptime.settime()
        except: pass
        return wlan, hostname
    return None, hostname

def conecta_mqtt(client_id, server, display_name):
    try:
        client = MQTTClient(client_id, server, user="icts", password="icts", keepalive=60)
        client.connect()
        print(f"MQTT {display_name} OK")
        return client
    except:
        return None

def obter_horario_utc3():
    t = time.localtime(time.time() + FUSO_HORARIO_SEGUNDOS)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*t[:6])

def atualizar_display_dados(leitura_num, temp, hum, horario):
    if oled:
        oled.fill(0)
        oled.text(f"L:{leitura_num} {horario[11:16]}", 0, 0)
        oled.text(f"T: {temp:.1f} C", 0, 25)
        oled.text(f"U: {hum:.1f} %", 0, 45)
        oled.show()

# ==================== Programa Principal ====================
leitura_numero = 0
wlan, hostname_placa = conecta_wifi()
client_nuvem = conecta_mqtt(hostname_placa, MQTT_SERVER_NUVEM, "Nuvem")
client_local = conecta_mqtt(hostname_placa, MQTT_SERVER_LOCAL, "Local")

while True:
    leitura_numero += 1
    
    try:
        # 1. Realiza a Medição
        time.sleep(2)
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        horario = obter_horario_utc3()
        
        # 2. Publicação MQTT
        msg = f"ID:{hostname_placa},L:{leitura_numero},H:{horario},T:{temp:.1f},U:{hum:.1f}"
        
        for client, server, topic in [(client_nuvem, MQTT_SERVER_NUVEM, TOPIC_PUB_NUVEM), 
                                      (client_local, MQTT_SERVER_LOCAL, TOPIC_PUB_LOCAL)]:
            if client:
                try: client.publish(topic, msg.encode())
                except: pass

        print(f"L#{leitura_numero} enviada em {horario[11:19]}")

        # 3. Ciclo de Espera de 10 minutos (600 segundos)
        # O display mostra por 30s, apaga por 10s e repete.
        segundos_passados = 0
        while segundos_passados < 600:
            
            # Parte A: Mostrar dados por 30 segundos
            atualizar_display_dados(leitura_numero, temp, hum, horario)
            for _ in range(30):
                if segundos_passados >= 600: break
                time.sleep(1)
                segundos_passados += 1
            
            # Parte B: Limpar display por 10 segundos
            if oled:
                oled.fill(0)
                oled.show()
            for _ in range(10):
                if segundos_passados >= 600: break
                time.sleep(1)
                segundos_passados += 1
                
    except Exception as e:
        print(f"Erro no loop: {e}")
        time.sleep(5)
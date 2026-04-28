import network
import time
import machine
from umqtt.simple import MQTTClient

# Importações do segundo programa
from machine import Pin, I2C
import ssd1306
import dht

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER = "192.168.15.8"
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
CLIENT_ID = "pico_w_dht_combined"
TOPIC_PUB_ALL = b"temperatura/umidade" # Tópico único para ambos os dados

# ==================== Configuração de Periféricos ====================
# Configuração I2C do OLED
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Configuração do DHT22
sensor = dht.DHT22(Pin(2))

# Configuração do botão
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# ==================== Funções de Conexão ====================
def conecta_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    oled.fill(0)
    oled.text("Conectando Wi-Fi", 0, 0)
    oled.show()
    while not wlan.isconnected():
        time.sleep(1)
    print("Conectado ao Wi-Fi:", wlan.ifconfig())
    return wlan

def conecta_mqtt():
    client = MQTTClient(CLIENT_ID, MQTT_SERVER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
    client.connect()
    oled.fill(0)
    oled.text("MQTT conectado", 0, 0)
    oled.show()
    print("Conectado ao broker MQTT")
    return client

# ==================== Funções para o DHT e OLED ====================
def mostrar_dados(temp, hum):
    oled.fill(0)
    oled.text("Temp: {:.1f} C".format(temp), 0, 20)
    oled.text("Umid: {:.1f} %".format(hum), 0, 40)
    oled.show()
    print("Temperatura: {:.1f} C, Umidade: {:.1f} %".format(temp, hum))

def aguardar_botao():
    oled.fill(0)
    oled.text("Pressione botao", 0, 20)
    oled.text("para continuar", 0, 35)
    oled.show()
    print("Aguardando botão para continuar...")
    while not botao.value():
        time.sleep(0.1)

# ==================== Programa Principal ====================
try:
    # 1. Conexão
    wlan = conecta_wifi()
    client = conecta_mqtt()

    while True:
        # 2. Leitura do sensor
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            mostrar_dados(temp, hum)
            
            # 3. Publicação no MQTT em um único tópico
            msg = "Temp={:.1f}, Umid={:.1f}".format(temp, hum)
            client.publish(TOPIC_PUB_ALL, msg.encode())
            print("Publicado:", msg)

        except OSError as e:
            oled.fill(0)
            oled.text("Erro sensor DHT", 0, 20)
            oled.show()
            print("Erro de leitura do sensor DHT:", e)
        
        # 4. Verificação de botão e temporização
        for _ in range(20):
            if botao.value():
                aguardar_botao()
            time.sleep(0.1)
        
except Exception as e:
    oled.fill(0)
    oled.text("ERRO CRITICO", 0, 20)
    oled.text(str(e), 0, 40)
    oled.show()
    print("Erro critico:", e)
    machine.reset()
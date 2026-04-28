import network
import time
import machine
from umqtt.simple import MQTTClient
import json
import ntptime
import binascii # Necessário para converter o MAC para string 

# Importações de periféricos
from machine import Pin, I2C
import ssd1306
import dht

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"
MQTT_SERVER = "192.168.15.14"
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_PUB_ALL = b"Mato_Temperatura" # LED de alimentação verde Pico W_11f0bb 

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
    
    # 1. Obtém o MAC address e cria um nome de host único
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_unico = "Pico W_" + mac_hex[-6:]
    
    # 2. Define o hostname antes de conectar
    wlan.config(hostname=hostname_unico)
    print(f"Tentando conectar com o nome de host: {hostname_unico}")
    
    # 3. Conecta à rede Wi-Fi
    wlan.connect(SSID, PASSWORD)
    oled.fill(0)
    oled.text("Conectando Wi-Fi", 0, 0)
    oled.show()
    
    while not wlan.isconnected():
        time.sleep(1)
    
    print("Conectado ao Wi-Fi:", wlan.ifconfig())
    
    # Sincroniza o relógio interno (RTC) com um servidor NTP
    try:
        ntptime.host = "a.ntp.br"
        ntptime.settime()
        print("Data e hora sincronizadas via NTP.")
    except Exception as e:
        print("Erro ao sincronizar NTP:", e)

    return wlan, hostname_unico # Retorna o nome de host único

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
    print("=== Leitura #{} ===".format(leitura_num))
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
leitura_numero = 0

try:
    # 1. Conexão
    wlan, hostname_placa = conecta_wifi()
    
    # Usa o hostname único como CLIENT_ID do MQTT
    client = conecta_mqtt(hostname_placa)

    while True:
        leitura_numero += 1
        
        # 2. Leitura do sensor com tempo de estabilização
        time.sleep(2)  # Adiciona uma pausa de 2 segundos antes da leitura
        
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            
            # Formata a data e hora do RTC para o envio
            rtc_tuple = time.localtime()
            #data_hora = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                rtc_tuple[0], rtc_tuple[1], rtc_tuple[2], rtc_tuple[3], rtc_tuple[4], rtc_tuple[5])# comentado porque estava criando a hora sem o UTC -3
                
            mostrar_dados(leitura_numero, temp, hum)
            
            # 3. Criação e publicação do JSON no MQTT
            dados_leitura = {
                "leitura_numero": leitura_numero,
                "temperatura": temp,
                "umidade": hum,
                #"data_hora": data_hora, # comentado devido UTC
                "hostname": hostname_placa
            }
            
            msg = json.dumps(dados_leitura)
            client.publish(TOPIC_PUB_ALL, msg.encode())
            print("Publicado:", msg)

        except OSError as e:
            oled.fill(0)
            oled.text("Erro sensor DHT", 0, 20)
            oled.show()
            print("Erro de leitura do sensor DHT:", e)
        
        # 4. Verificação de botão e temporização
        # Espera 5 minutos (300 segundos) para a próxima leitura
        for _ in range(300):
            if botao.value():
                aguardar_botao()
            time.sleep(1)
            
except Exception as e:
    oled.fill(0)
    oled.text("ERRO CRITICO", 0, 20)
    oled.text(str(e), 0, 40)
    oled.show()
    print("Erro critico:", e)
    machine.reset()
    

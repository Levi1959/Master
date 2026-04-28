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

# ==================== Configuração de Periféricos ====================
# Configuração do Watchdog (máximo de 8000 ms)
# O WDT precisa ser alimentado frequentemente para não reiniciar a placa.
wdt = WDT(timeout=8000)

# Configuração I2C do OLED
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
except Exception as e:
    print(f"Erro ao inicializar o OLED: {e}. O programa continuará sem o display.")
    oled = None

# Configuração do DHT22
sensor = dht.DHT22(Pin(2))

# Configuração do botão
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"

# Broker da Nuvem (Oracle)
MQTT_SERVER_NUVEM = "163.176.182.91"
MQTT_PORT_NUVEM = 1883
MQTT_USER_NUVEM = "icts"
MQTT_PASSWORD_NUVEM = "icts"
TOPIC_PUB_NUVEM = b"Mato_Temperatura"

# Broker Local (Mosquitto)
MQTT_SERVER_LOCAL = "192.168.15.14"
MQTT_PORT_LOCAL = 1883
MQTT_USER_LOCAL = "icts"
MQTT_PASSWORD_LOCAL = "icts"
TOPIC_PUB_LOCAL = b"Mato_Temperatura_Local"

# ==================== Funções de Conexão ====================
def show_oled(text, line=0):
    """Função auxiliar para mostrar texto no OLED, se disponível."""
    if oled:
        oled.fill(0)
        oled.text(text, 0, line)
        oled.show()
        
def conecta_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    
    wlan.config(hostname=hostname_placa)
    print(f"Tentando conectar com o nome de host: {hostname_placa}")
    
    wlan.connect(SSID, PASSWORD)
    show_oled("Conectando Wi-Fi")
    
    max_tentativas_wifi = 90
    tentativas_wifi = 0
    while not wlan.isconnected() and tentativas_wifi < max_tentativas_wifi:
        wdt.feed()
        time.sleep(1)
        tentativas_wifi += 1
    
    if not wlan.isconnected():
        print("Falha na conexão Wi-Fi.")
        return None, None

    print("Conectado ao Wi-Fi:", wlan.ifconfig())
    
    try:
        ntptime.host = "a.ntp.br"
        ntptime.settime()
        print("Data e hora sincronizadas via NTP.")
    except Exception as e:
        print("Erro ao sincronizar NTP:", e)

    return wlan, hostname_placa

def conecta_mqtt(client_id, server, port, user, password, display_text):
    """Função para conectar a um único broker MQTT."""
    try:
        client = MQTTClient(client_id, server, port=port, user=user, password=password)
        client.connect()
        print(f"Conectado ao broker MQTT: {server}")
        show_oled(display_text)
        return client
    except Exception as e:
        print(f"Falha na conexão MQTT com {server}: {e}")
        show_oled("Erro MQTT!")
        return None

# ==================== Funções para o DHT e OLED ====================
def mostrar_dados(leitura_num, temp, hum):
    if oled:
        oled.fill(0)
        oled.text(f"Leitura #{leitura_num}", 0, 0)
        oled.text(f"Temp: {temp:.1f} C", 0, 20)
        oled.text(f"Umid: {hum:.1f} %", 0, 40)
        oled.show()

# ==================== Programa Principal ====================
leitura_numero = 0

try:
    wlan, hostname_placa = conecta_wifi()
    if wlan is None:
        show_oled("Erro Wi-Fi!")
        time.sleep(5)
        machine.reset()
    
    client_nuvem = conecta_mqtt(hostname_placa, MQTT_SERVER_NUVEM, MQTT_PORT_NUVEM, MQTT_USER_NUVEM, MQTT_PASSWORD_NUVEM, "Nuvem ON!")
    client_local = conecta_mqtt(hostname_placa, MQTT_SERVER_LOCAL, MQTT_PORT_LOCAL, MQTT_USER_LOCAL, MQTT_PASSWORD_LOCAL, "Local ON!")
    
    while True:
        wdt.feed()
        leitura_numero += 1
        
        # Leitura do sensor
        try:
            time.sleep(2)
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            
            mostrar_dados(leitura_numero, temp, hum)

            print(f"=== Leitura #{leitura_numero} ===")
            print(f"Temperatura: {temp:.1f} C, Umidade: {hum:.1f} %")
            
            dados_leitura = {
                "leitura_numero": leitura_numero,
                "temperatura": temp,
                "umidade": hum,
                "hostname": hostname_placa
            }
            msg = json.dumps(dados_leitura)
            
            # Tenta publicar no broker da nuvem
            if client_nuvem:
                try:
                    client_nuvem.publish(TOPIC_PUB_NUVEM, msg.encode())
                    print("Publicado na nuvem: " + msg)
                except Exception as e:
                    print(f"Falha ao publicar na nuvem: {e}. Tentando reconectar...")
                    client_nuvem = conecta_mqtt(hostname_placa, MQTT_SERVER_NUVEM, MQTT_PORT_NUVEM, MQTT_USER_NUVEM, MQTT_PASSWORD_NUVEM, "Recon. Nuvem")

            # Tenta publicar no broker local
            if client_local:
                try:
                    client_local.publish(TOPIC_PUB_LOCAL, msg.encode())
                    print("Publicado localmente: " + msg)
                except Exception as e:
                    print(f"Falha ao publicar localmente: {e}. Tentando reconectar...")
                    client_local = conecta_mqtt(hostname_placa, MQTT_SERVER_LOCAL, MQTT_PORT_LOCAL, MQTT_USER_LOCAL, MQTT_PASSWORD_LOCAL, "Recon. Local")
            
            # Se ambos os clientes falharam, reinicia a placa
            if not client_nuvem and not client_local:
                print("Ambos os brokers falharam. Reiniciando a placa.")
                show_oled("Falha total!")
                time.sleep(5)
                machine.reset()

        except OSError as e:
            show_oled("Erro sensor", 20)
            print("Erro de leitura do sensor:", e)
        
        print("Iniciando espera de 3 minutos...")
        for _ in range(180):
            wdt.feed()
            if botao.value():
                pass
            time.sleep(1)
            
except Exception as e:
    show_oled("ERRO CRITICO", 20)
    show_oled(str(e), 40)
    print("Erro critico:", e)
    machine.reset()
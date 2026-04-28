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
TOPIC_PUB_ALL = b"Mato_Temperatura" # Led Vermelho Pic0_W11f60f

# ==================== Funções de Conexão ====================
def conecta_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    
    wlan.config(hostname=hostname_placa)
    print(f"Tentando conectar com o nome de host: {hostname_placa}")
    
    wlan.connect(SSID, PASSWORD)
    oled.fill(0)
    oled.text("Conectando Wi-Fi", 0, 0)
    oled.show()
    
    # Aguarda a conexão Wi-Fi. Alimenta o WDT a cada segundo.
    max_tentativas_wifi = 90  # Tentar por 30 segundos
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
        print("Data e hora sincronizadas via NTP.")
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
            
            dados_leitura = {
                "leitura_numero": leitura_numero,
                "temperatura": temp,
                "umidade": hum,
                "hostname": hostname_placa
            }
            
            msg = json.dumps(dados_leitura)
            
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
        
        print("Iniciando espera de 3 minutos...")
        for _ in range(180):
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
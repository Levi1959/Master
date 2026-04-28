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

# Configuração I2C do OLED (Pinos 0 e 1)
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    print("OLED inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar o OLED: {e}. O programa continuará sem o display.")
    oled = None

# Configuração do DHT22 (Pino 2)
sensor = dht.DHT22(Pin(2))

# Configuração do botão (Pino 3)
botao = Pin(3, Pin.IN, Pin.PULL_DOWN)

# Configuração do SD Card (SPI 0)
SD_SCK = 18
SD_MISO = 16
SD_MOSI = 19
SD_CS = 17

# Variáveis globais de controle
SD_MOUNT_POINT = "/sd"
LOG_FILE = "" 
sd = None 

# ==================== Configurações Wi-Fi e MQTT ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"

# Broker da Nuvem (Oracle)
MQTT_SERVER_NUVEM = "163.176.182.91"
MQTT_PORT_NUVEM = 1883
MQTT_USER_NUVEM = "icts"
MQTT_PASSWORD_NUVEM = "icts"
TOPIC_PUB_NUVEM = b"Urbano_Temperatura"

# Broker Local (Mosquitto)
MQTT_SERVER_LOCAL = "192.168.15.14"
MQTT_PORT_LOCAL = 1883
MQTT_USER_LOCAL = "icts"
MQTT_PASSWORD_LOCAL = "icts"
TOPIC_PUB_LOCAL = b"Urbano_Temperatura_Local"

# Fuso horário de Brasília (UTC-3) em segundos
FUSO_HORARIO_SEGUNDOS = -3 * 3600

# Variáveis Globais de Estado
hostname_placa = "Pico W_Default"
sincronizacao_sucesso = False
client_nuvem = None
client_local = None
wlan = None
leitura_numero = 0 # Variável de contagem principal

# ==================== Funções Auxiliares ====================

def show_oled(text, line=0, clear_line=True):
    """Função auxiliar para mostrar texto no OLED."""
    if oled:
        if clear_line:
            oled.rect(0, line, 128, 12, 0, True)
        oled.text(text, 0, line)
        oled.show()
        
def show_oled_full_clear(text1, text2=""):
    """Limpa tudo e mostra duas linhas de texto."""
    if oled:
        oled.fill(0)
        oled.text(text1, 0, 0)
        oled.text(text2, 0, 20)
        oled.show()

def obter_horario_rtc(ajustado=True):
    """Retorna o horário formatado, ajustado (UTC-3) e o tuple (data/hora)."""
    internal_time_seconds = time.time()
    offset = FUSO_HORARIO_SEGUNDOS if ajustado else 0
    local_time_tuple = time.localtime(internal_time_seconds + offset)
    horario_formatado = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*local_time_tuple[:6])
    return horario_formatado, local_time_tuple

def conecta_mqtt(client_id, server, port, user, password, display_text):
    """Função para conectar a um único broker MQTT."""
    try:
        client = MQTTClient(client_id, server, port=port, user=user, password=password)
        client.connect()
        print(f"Conectado ao broker MQTT: {server}")
        show_oled_full_clear(f"MQTT {display_text} OK!", "")
        time.sleep(1)
        return client
    except Exception as e:
        print(f"Falha na conexão MQTT com {server}: {e}")
        show_oled_full_clear(f"MQTT {display_text} ERRO!", "Tentando mais tarde.")
        time.sleep(1)
        return None

def tentar_reconexao_mqtt(client, server, port, user, password, display_text):
    """Tenta reconectar um cliente MQTT se ele for None."""
    global hostname_placa
    if client is None and wlan and wlan.isconnected():
        return conecta_mqtt(hostname_placa, server, port, user, password, display_text)
    return client

def verificar_e_reconectar_wifi():
    """Tenta reativar e reconectar o Wi-Fi se não estiver ativo."""
    global wlan, sincronizacao_sucesso, client_nuvem, client_local
    
    if wlan is None or not wlan.isconnected():
        print("Wi-Fi offline. Tentando reconectar...")
        
        temp_wlan = network.WLAN(network.STA_IF)
        temp_wlan.active(True)
        
        show_oled_full_clear("Recon. Wi-Fi", f"Host: {hostname_placa}")
        temp_wlan.connect(SSID, PASSWORD)
        
        time.sleep(2) 
        
        for _ in range(10): # Timeout reduzido para reconexão
            if temp_wlan.isconnected():
                wlan = temp_wlan
                print("Wi-Fi reconectado!")
                show_oled_full_clear("Wi-Fi ON!", "")
                
                # Tenta sincronizar NTP novamente para manter a precisão
                try:
                    ntptime.host = "pool.ntp.org" # Tentativa de reconexão
                    ntptime.settime()
                    sincronizacao_sucesso = True
                except:
                    sincronizacao_sucesso = False
                    
                client_nuvem = None
                client_local = None
                return True
            time.sleep(1)
        
        temp_wlan.active(False)
        wlan = None
        return False
    
    return True


def conecta_wifi_e_mqtt():
    """Tenta conectar Wi-Fi, sincronizar NTP e conectar MQTT. Retorna status de sincronização."""
    global hostname_placa, sincronizacao_sucesso, wlan, client_nuvem, client_local
    
    # 1. Configura e Conecta Wi-Fi
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    wlan.config(hostname=hostname_placa)
    
    show_oled_full_clear("Conectando Wi-Fi", hostname_placa)
    wlan.connect(SSID, PASSWORD)
    
    time.sleep(2) 
    
    # Timeout de 30 segundos
    for tentativa in range(1, 31):
        if wlan.isconnected():
            break
        time.sleep(1)
        show_oled(f"Tentativa {tentativa}/30...", 40)
    
    if not wlan.isconnected():
        print("Falha na conexão Wi-Fi. Continuando no modo offline.")
        show_oled_full_clear("Wi-Fi FALHOU", "Modo Offline")
        wlan.active(False) 
        wlan = None
        sincronizacao_sucesso = False
        return False 

    print(f"Conectado ao Wi-Fi: {wlan.ifconfig()}")
    show_oled_full_clear("Wi-Fi OK (1/3)", "Tentando NTP.")
    
    # 2. Sincroniza NTP
    try:
        ntptime.host = "pool.ntp.org" # ALTERADO para pool.ntp.org
        ntptime.settime()
        sincronizacao_sucesso = True
        print("Data e hora sincronizadas via NTP.")
        horario_formatado, local_time_tuple = obter_horario_rtc(ajustado=False)
        show_oled_full_clear("NTP OK (2/3)", f"Hora: {horario_formatado[11:19]}")
        time.sleep(1)
    except Exception as e:
        print(f"Erro ao sincronizar NTP: {e}.")
        sincronizacao_sucesso = False
        show_oled_full_clear("NTP FALHOU", "Continuando sem sync.")
        time.sleep(1)
        horario_formatado, local_time_tuple = obter_horario_rtc(ajustado=False)

    # 3. Conecta MQTT
    client_nuvem = conecta_mqtt(hostname_placa, MQTT_SERVER_NUVEM, MQTT_PORT_NUVEM, MQTT_USER_NUVEM, MQTT_PASSWORD_NUVEM, "NUVEM")
    client_local = conecta_mqtt(hostname_placa, MQTT_SERVER_LOCAL, MQTT_PORT_LOCAL, MQTT_USER_LOCAL, MQTT_PASSWORD_LOCAL, "LOCAL")
    
    return True 


def inicializa_sd_card(data_hora_tuple):
    """Inicializa, monta o cartão SD e define o nome do arquivo com a data."""
    global sd, LOG_FILE
    
    if sd is not None:
        return sd

    show_oled_full_clear("Inicializando SD...", "")
    
    # GERA O NOME DO ARQUIVO: log_DD_MM_YYYY.csv
    ano, mes, dia, *_ = data_hora_tuple
    LOG_FILE = "log_{:02}_{:02}_{:04}.csv".format(dia, mes, ano)
    
    try:
        # Tenta inicializar SD Card (SPI0)
        spi = SPI(0, baudrate=2000000, polarity=0, phase=0,
                  miso=Pin(SD_MISO), sck=Pin(SD_SCK), mosi=Pin(SD_MOSI))
        
        cs = Pin(SD_CS, Pin.OUT)
        sd_instancia = sdcard.SDCard(spi, cs)
        os.mount(sd_instancia, SD_MOUNT_POINT)
        
        # SUCESSO
        sd = sd_instancia 
        print(f"Cartão SD montado com sucesso em {SD_MOUNT_POINT}")
        print(f"Arquivo de log: {LOG_FILE}")
        show_oled_full_clear("SD Card OK!", LOG_FILE)
        
        # Cria o cabeçalho se o arquivo for novo
        log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
        try:
            with open(log_path, "r"):
                pass
        except OSError:
            with open(log_path, "a") as f:
                header = "Leitura,Horario,Temperatura(C),Umidade(%),Dispositivo\n"
                f.write(header)
                print("Cabeçalho do arquivo de log criado.")
        
        return sd
        
    except Exception as e:
        print(f"Falha ao inicializar/montar o SD Card: {e}")
        show_oled_full_clear("SD FALHOU", "Tentando mais tarde.")
        sd = None 
        return None

def log_data_sd(sd_instancia, leitura_numero, horario, temp, hum, hostname):
    """Grava os dados no arquivo CSV do SD Card."""
    global sd, LOG_FILE
    
    if sd_instancia is None:
        return False

    data_line = f"{leitura_numero},{horario},{temp:.1f},{hum:.1f},{hostname}\n" 
    log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
    
    try:
        with open(log_path, "a") as f:
            f.write(data_line)
        return True 
        
    except Exception as e:
        # Erro de escrita CRÍTICO
        print(f"ERRO CRÍTICO ao escrever no SD Card: {e}. Desmontando...")
        try:
            os.umount(SD_MOUNT_POINT)
            sd = None 
            print("SD Card desmontado após erro CRÍTICO de escrita.")
        except:
            pass
        return False 

def mostrar_dados(leitura_num_display, temp, hum, horario, sd_ok, sync_ok, mqtt_cloud_ok, mqtt_local_ok, wifi_ok):
    """Atualiza o display OLED com os dados mais recentes."""
    if oled:
        # Linha 0: Leitura e Hora
        show_oled(f"L{leitura_num_display} {horario[11:16]}", 0, True)
        
        # Linha 1: Data / SYNC
        status_sync = "SYNC OK" if sync_ok else "SEM SYNC"
        show_oled(f"{horario[0:10]} / {status_sync}", 20, True)
        
        # Linha 2: SD Card / WiFi
        status_sd = "SD OK" if sd_ok else "SD FALHA"
        status_wifi = "WiFi OK" if wifi_ok else "WiFi OFF"
        show_oled(f"{status_sd} / {status_wifi}", 30, True)

        # Linha 3: MQTT Status
        status_mqtt = f"C: {'OK' if mqtt_cloud_ok else 'F'} L: {'OK' if mqtt_local_ok else 'F'}"
        show_oled(f"MQTT: {status_mqtt}", 40, True)
        
        # Linhas de Dados
        show_oled(f"T: {temp:.1f} C", 50, True)
        show_oled(f"U: {hum:.1f} %", 60, True)
        oled.show()


# ==================== Programa Principal ====================

try:
    show_oled_full_clear("INICIANDO SISTEMA", "v2.7 - NTP pool.ntp.org")
    time.sleep(1)
    
    # 1. Tenta conectar Wi-Fi, NTP e MQTTs (Prioridade)
    wifi_conectado = conecta_wifi_e_mqtt()
    
    # Obtém a data e hora (sincronizada ou interna) para nomear o arquivo
    # Nota: A data será a data do RTC se o NTP falhar.
    _, data_hora_tuple_inicial = obter_horario_rtc(ajustado=True)
    
    # 2. Inicializa o SD Card (CRÍTICO NA INICIALIZAÇÃO)
    if inicializa_sd_card(data_hora_tuple_inicial) is None:
        show_oled_full_clear("ERRO SD CRITICO!", "PARADA INICIAL")
        while True: 
            time.sleep(10)

    while True:
        leitura_numero += 1
        
        # --- LÓGICA DE TRATAMENTO DE CONEXÃO ---
        if not wifi_conectado:
            wifi_conectado = verificar_e_reconectar_wifi()

        if wifi_conectado:
            client_nuvem = tentar_reconexao_mqtt(client_nuvem, MQTT_SERVER_NUVEM, MQTT_PORT_NUVEM, MQTT_USER_NUVEM, MQTT_PASSWORD_NUVEM, "NUVEM")
            client_local = tentar_reconexao_mqtt(client_local, MQTT_SERVER_LOCAL, MQTT_PORT_LOCAL, MQTT_USER_LOCAL, MQTT_PASSWORD_LOCAL, "LOCAL")
        # ----------------------------------------

        # --- LÓGICA DE TRATAMENTO DO SD CARD ---
        if sd is None:
            # Se o SD falhar, ele tentará se re-inicializar com a data e hora atual.
            _, data_hora_tuple_atual = obter_horario_rtc(ajustado=True)
            inicializa_sd_card(data_hora_tuple_atual)
        # ----------------------------------------
        
        # Leitura do sensor
        try:
            time.sleep(2)
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            
            horario, _ = obter_horario_rtc()
            
            # Prepara dados
            msg_texto = f"{leitura_numero},{horario},{temp:.1f},{hum:.1f},{hostname_placa}"

            # 3. LOG NO SD CARD (Não-Crítico)
            sd_ok = log_data_sd(sd, leitura_numero, horario, temp, hum, hostname_placa)

            # 4. OPCIONAL: Publicação MQTT (Não-Crítico)
            nuvem_publicada = False
            if client_nuvem:
                try:
                    client_nuvem.publish(TOPIC_PUB_NUVEM, msg_texto.encode())
                    nuvem_publicada = True
                except Exception as e:
                    print(f"Falha ao publicar na nuvem: {e}. Desconectando...")
                    client_nuvem = None 
            
            local_publicada = False
            if client_local:
                try:
                    client_local.publish(TOPIC_PUB_LOCAL, msg_texto.encode())
                    local_publicada = True
                except Exception as e:
                    print(f"Falha ao publicar localmente: {e}. Desconectando...")
                    client_local = None 
            
            # 5. Atualiza o display com todos os status
            mostrar_dados(leitura_numero, temp, hum, horario, sd_ok, sincronizacao_sucesso, nuvem_publicada, local_publicada, wifi_conectado)

        except OSError as e:
            show_oled("Erro sensor", 40)
            print("Erro de leitura do sensor (OSError):", e)
            
        
        print(f"Leitura #{leitura_numero}. Iniciando espera de 10 minutos...")
        # 600 segundos = 10 minutos
        for _ in range(600):
            time.sleep(1)
            
except Exception as e:
    show_oled_full_clear("ERRO CRITICO", str(e))
    print("Erro critico:", e)
    
    if sd is not None:
        try:
            os.umount(SD_MOUNT_POINT)
            print("SD Card desmontado com sucesso no erro crítico.")
        except:
            pass
            
    # machine.reset()
    print("Programa parado devido a erro crítico.")
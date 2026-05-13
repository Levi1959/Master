import time
import machine
import os
import binascii

from machine import Pin, I2C, SPI
import network
import ntptime
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

# ==================== Configuração do SD Card (SPI 0) ====================
# PINAGEM: MISO=GP16, SCK=GP18, MOSI=GP19, CS=GP17
SD_SCK = 18
SD_MISO = 16
SD_MOSI = 19
SD_CS = 17

LOG_FILE = "log_temperatura.csv"
SD_MOUNT_POINT = "/sd"
sd = None # Variável global para rastrear a instância do SD Card

# ==================== Variáveis e Constantes Globais ====================
SSID = "Eliete_2G"
PASSWORD = "senha01957"

# Fuso horário de Brasília (UTC-3) em segundos
FUSO_HORARIO_SEGUNDOS = -3 * 3600

# Variável para armazenar a instância do Wi-Fi
wlan = None

# ==================== Funções Auxiliares ====================

def show_oled(text, line=0):
    """Função auxiliar para mostrar texto no OLED."""
    if oled:
        if line == 0:
            oled.fill(0)
        elif line > 0:
            oled.rect(0, line, 128, 12, 0, True)

        oled.text(text, 0, line)
        oled.show()

def obter_horario_rtc(ajustado=True):
    """Retorna o horário formatado, ajustado ou bruto (para mostrar a hora exata)."""
    internal_time_seconds = time.time()
    
    # Aplica o fuso horário se ajustado for True (comportamento padrão)
    offset = FUSO_HORARIO_SEGUNDOS if ajustado else 0
    
    local_time_tuple = time.localtime(internal_time_seconds + offset)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*local_time_tuple[:6])


def conecta_wifi_e_sincroniza():
    """Conecta ao Wi-Fi, sincroniza NTP, exibe a hora e desliga o rádio."""
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    mac_bytes = wlan.config('mac')
    mac_hex = binascii.hexlify(mac_bytes).decode()
    hostname_placa = "Pico W_" + mac_hex[-6:]
    wlan.config(hostname=hostname_placa)
    
    wlan.connect(SSID, PASSWORD)
    show_oled("Conectando Wi-Fi", 0)
    
    # Timeout de 30 segundos
    for tentativa in range(1, 31):
        show_oled(f"Tentativa {tentativa}/30...", 40)
        time.sleep(1)
        
        if wlan.isconnected():
            print("Conectado ao Wi-Fi. Tentando NTP.")
            show_oled("Conectado! (1/2)", 20)
            
            # 2. Sincroniza NTP
            try:
                ntptime.host = "a.ntp.br"
                ntptime.settime()
                
                # Obtém a hora sincronizada e formatada (sem o fuso, pois NTP usa UTC)
                hora_sincronizada_utc = obter_horario_rtc(ajustado=False)[11:19]
                
                print("Data e hora sincronizadas via NTP.")
                show_oled(f"Hora: {hora_sincronizada_utc}", 20) # Exibe a hora atual!
                
                time.sleep(3) # Tempo extra para o usuário visualizar a hora

                # 3. DESLIGA O WI-FI
                wlan.active(False)
                print("Wi-Fi desativado para operação em campo.")
                show_oled("Modo Campo ON", 20)
                return hostname_placa, True
                
            except Exception as e:
                print(f"Erro ao sincronizar NTP: {e}. Desligando Wi-Fi.")
                wlan.active(False)
                show_oled("Erro NTP", 20)
                return hostname_placa, False
    
    # Se falhar a conexão após 30 tentativas
    print("Falha na conexão Wi-Fi. Operando com hora interna.")
    wlan.active(False)
    show_oled("Falha Wi-Fi", 20)
    return hostname_placa, False


def inicializa_sd_card():
    """Inicializa e monta o cartão SD."""
    global sd # Necessário para modificar a variável global 'sd'
    
    try:
        # Baudrate de 2MHz para estabilidade
        spi = SPI(0, baudrate=2000000, polarity=0, phase=0,
                  miso=Pin(SD_MISO), sck=Pin(SD_SCK), mosi=Pin(SD_MOSI))
        
        cs = Pin(SD_CS, Pin.OUT)
        # Tenta inicializar o SD Card
        sd = sdcard.SDCard(spi, cs)
        os.mount(sd, SD_MOUNT_POINT)
        print(f"Cartão SD montado com sucesso em {SD_MOUNT_POINT}")
        show_oled("SD Card OK", 10)
        
        # Cria o cabeçalho se o arquivo for novo
        log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
        if LOG_FILE not in os.listdir(SD_MOUNT_POINT):
              with open(log_path, "a") as f:
                header = "Leitura,Horario,Temperatura(C),Umidade(%),Dispositivo\n"
                f.write(header)
                print("Cabeçalho do arquivo de log criado.")
        return sd
        
    except Exception as e:
        print(f"Falha ao inicializar/montar o SD Card: {e}")
        show_oled("Erro SD Card!", 10)
        sd = None # Garante que a global 'sd' é None em caso de falha
        return None

def log_data_sd(sd_instancia, leitura_num, horario, temp, hum, hostname):
    """
    Grava os dados no arquivo CSV do SD Card.
    Retorna True em caso de sucesso, False em caso de falha crítica.
    Em caso de falha, desmonta o SD e seta a global 'sd' para None.
    """
    global sd # Necessário para modificar a variável global 'sd' após erro
    
    if sd_instancia is None:
        # Se não há instância, o log falhou antes de começar
        return False

    data_line = f"{leitura_num},{horario},{temp:.1f},{hum:.1f},{hostname}\n"
    log_path = f"{SD_MOUNT_POINT}/{LOG_FILE}"
    
    try:
        with open(log_path, "a") as f:
            f.write(data_line)
        print("Log gravado no SD Card.")
        return True # Sucesso
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao escrever no SD Card: {e}. Desmontando...")
        
        # Tenta desmontar após o erro de escrita
        try:
            os.umount(SD_MOUNT_POINT)
            sd = None # CRÍTICO: Seta a global 'sd' para None, forçando a parada
            print("SD Card desmontado após erro CRÍTICO de escrita.")
        except:
            pass
            
        return False # Falha


def mostrar_dados(leitura_num, temp, hum, horario, sd_ok, sync_ok):
    """Atualiza o display OLED com os dados mais recentes."""
    if oled:
        # Linha 0: Leitura e Hora
        oled.rect(0, 0, 128, 12, 0, True)
        oled.text(f"L{leitura_num} {horario[11:16]}", 0, 0)
        
        # Linha 1: Data e Status
        oled.rect(0, 20, 128, 12, 0, True)
        oled.text(horario[0:10], 0, 20)
        
        # Status
        status_sync = "OK" if sync_ok else "SEM SYNC"
        status_sd = "SD OK" if sd_ok else "SD FALHA" # Embora se falhar vai parar
        oled.text(f"{status_sd} / {status_sync}", 70, 20)
        
        # Linhas de Dados
        oled.rect(0, 30, 128, 24, 0, True)
        oled.text(f"T: {temp:.1f} C", 0, 40)
        oled.text(f"U: {hum:.1f} %", 0, 50)
        oled.show()

# ==================== Programa Principal ====================
leitura_numero = 0
sincronizacao_sucesso = False

try:
    show_oled("INICIANDO", 0)
    
    # PASSO 1: Sincroniza (só acontece uma vez)
    hostname_placa, sincronizacao_sucesso = conecta_wifi_e_sincroniza()
        
    # PASSO 2: Inicializa o SD Card (seta a variavel global 'sd')
    if inicializa_sd_card() is None:
        # Se a inicialização do SD falhar, entramos imediatamente no loop de erro crítico.
        show_oled("ERRO SD CRITICO!", 0)
        show_oled("PARADA INICIAL", 20)
        print("Falha na inicialização do SD. Parando execução.")
        while True: # Loop de parada de execução
            time.sleep(10)


    while True:
        leitura_numero += 1
        
        # Leitura do sensor
        try:
            time.sleep(2)
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            
            # Obtém a hora a partir do RTC (que agora está sincronizado)
            horario = obter_horario_rtc()
            
            # Neste ponto, 'sd' global deve ser a instância montada.
            sd_ok = sd is not None
            
            # ** Verificação de Estado CRÍTICA **
            if not sd_ok:
                # Se 'sd' for None aqui, é porque falhou durante o log anterior e fomos forçados a desmontar.
                show_oled("ERRO SD CRITICO!", 0)
                show_oled("PARADA DE EXEC.", 20)
                print("SD Card desmontado após erro de escrita. Parando execução.")
                while True: # Loop de parada de execução, forçando a parada
                    time.sleep(10)


            mostrar_dados(leitura_numero, temp, hum, horario, sd_ok, sincronizacao_sucesso)

            # PASSO 3: TENTA LOG NO SD CARD
            # Passa a variável global 'sd' para o log
            if not log_data_sd(sd, leitura_numero, horario, temp, hum, hostname_placa):
                # Se o log falhou, a função log_data_sd já desmontou e setou sd=None.
                show_oled("ERRO SD GRAVACAO!", 0)
                show_oled("PARADA DE EXEC.", 20)
                print("Falha CRÍTICA na gravação do SD. Parando execução.")
                while True: # Loop de parada de execução, forçando a parada
                    time.sleep(10)
        
        except OSError as e:
            # Tratamento de erros de leitura do sensor
            show_oled("Erro sensor", 40)
            print("Erro de leitura do sensor (OSError):", e)
        
        # Pausa de 20 segundos
        for _ in range(20):
            time.sleep(1)
            
except Exception as e:
    # Tratamento de erro geral e reset
    show_oled("ERRO CRITICO", 20)
    show_oled(str(e), 40)
    print("Erro critico:", e)
    
    if sd is not None:
        try:
            os.umount(SD_MOUNT_POINT)
            print("SD Card desmontado com sucesso no erro crítico.")
        except:
            pass
            
    #machine.reset() # Removido o reset para permitir que o erro seja visualizado no console
    print("Programa parado devido a erro crítico.")

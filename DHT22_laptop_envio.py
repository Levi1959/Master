# Importa bibliotecas necessárias
from machine import Pin, I2C, RTC
import dht
import utime
import ssd1306
import sys
import network 
import select

# Este programa funciona independente da segunda parte que deve rodar no laptop na mesma porta COM que este programa roda.
# Porém a segunda parte somente funciona se rodar antes dos 15 segundos de aguarde da comunicação com o microcontrolador. 
# --- CONFIGURAÇÕES DE HARDWARE ---
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
OLED_LARGURA = 128
OLED_ALTURA = 64
# Inicialização do OLED
try:
    oled = ssd1306.SSD1306_I2C(OLED_LARGURA, OLED_ALTURA, i2c)
except Exception as e:
    # Se a inicialização falhar (OLED não conectado), exibe um aviso.
    print(f"ERRO: Falha ao inicializar OLED: {e}")
    oled = None # Define oled como None para evitar erros de chamada

PINO_DHT = 2
sensor = dht.DHT22(Pin(PINO_DHT))
rtc = RTC() 

# Objeto para monitoramento de serial não-bloqueante
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

# --- VARIÁVEIS DE REGISTRO E ID ---
contagem = 0
INTERVALO_LEITURA = 20 # segundos
ID_DISPOSITIVO = "Pico W_OFFLINE"
ID_DISPLAY = "DHT22_OFFLINE"
ultima_sincronizacao = 0


# --- FUNÇÕES DE AJUSTE DE TEMPO ---

def formatar_data(data_tuple):
    """Formata a data para uma string AAAA-MM-DD."""
    return "{:04d}-{:02d}-{:02d}".format(data_tuple[0], data_tuple[1], data_tuple[2])

def formatar_hora(data_tuple):
    """Formata a hora para uma string HH:MM:SS."""
    return "{:02d}:{:02d}:{:02d}".format(data_tuple[4], data_tuple[5], data_tuple[6])

# --- FUNÇÕES DE INICIALIZAÇÃO (COM PAUSA) ---

def exibir_oled(texto, linha, limpar=False):
    """Auxiliar para exibir texto no OLED se estiver disponível."""
    if oled:
        if limpar:
            oled.fill(0)
        oled.text(texto, 0, linha)
        oled.show()

def sincronizar_rtc_serial():
    """Aguarda o laptop iniciar, envia o sinal e processa o comando de hora."""
    global ID_DISPOSITIVO, ID_DISPLAY, ultima_sincronizacao
    
    exibir_oled(ID_DISPLAY, 0, limpar=True)
    exibir_oled("Aguardando SYNC...", 10)
    
    # Tenta obter o ID
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac_bytes = wlan.config('mac')
        mac_str = ''.join('{:02x}'.format(b) for b in mac_bytes)
        ultimos_4 = mac_str[-4:].upper()
        ID_DISPOSITIVO = f"Pico W_{ultimos_4}"
        ID_DISPLAY = f"DHT22_{ultimos_4}"
        wlan.active(False) 
    except:
        ID_DISPOSITIVO = "Pico W_OFFLINE"
        ID_DISPLAY = "DHT22_OFFLINE"

    exibir_oled("PAUSA de 15s...", 30)
    utime.sleep(15) 
    
    print("READY_TO_SYNC") 
    
    exibir_oled("Aguardando comando...", 40)
    
    # Loop para aguardar a hora do PC por 10 segundos
    start_time = utime.time()
    sync_received = False
    
    while utime.time() - start_time < 10:
        if poll.poll(100): # Checa a cada 100ms se há dados na serial
            try:
                comando_completo = sys.stdin.readline().strip()
                
                # --- NOVO PARSING ROBUSTO PARA RTC_SET: ---
                if comando_completo.startswith("RTC_SET:"):
                    # Exemplo: RTC_SET:2025,10,5,6,11,10,0
                    dados_hora_str = comando_completo.split(':')[1]
                    dados_hora = [int(x.strip()) for x in dados_hora_str.split(',')]
                    
                    # O RTC espera: (ano, mês, dia, weekday, hora, minuto, segundo)
                    if len(dados_hora) >= 7:
                        # Define a hora, adicionando microssegundo 0
                        rtc.datetime(tuple(dados_hora[:7] + [0])) 
                        sync_received = True
                        break
                # ----------------------------------------
            except Exception as e:
                # Ignora erros de parsing
                print(f"ERRO DE PARSING: {e}")
                pass
    
    if sync_received:
        exibir_oled("SYNC OK!", 50)
        print("RTC_SET_SUCCESS") 
        ultima_sincronizacao = utime.time()
        utime.sleep(2) # Pausa para estabilização
        return True
    else:
        exibir_oled("SYNC FALHOU", 50)
        print("RTC_NOT_SET")
        utime.sleep(2)
        return False


def exibir_oled_dados(temp, umid, cont):
    """Função para limpar e escrever no display OLED com dados."""
    if not oled: return
    
    oled.fill(0)    
    data_hora_tuple = rtc.datetime()
    
    oled.text(f"{ID_DISPLAY}", 0, 0)
    oled.text(f"Coleta: {cont}", 0, 10)
    oled.text("------------------", 0, 20)
    
    hora_str = formatar_hora(data_hora_tuple)
    oled.text(f"Hora: {hora_str}", 0, 30)
    
    oled.text("Temp:", 0, 45)
    oled.text(f"{temp:.1f} C", 60, 45)
    
    oled.text("Umid:", 0, 55)
    oled.text(f"{umid:.1f} %", 60, 55)
    
    oled.show()


def coletar_e_enviar():
    """Realiza a coleta, exibe e envia os dados no formato CSV (usando RTC)."""
    global contagem, ultima_sincronizacao
    
    try:
        sensor.measure()
        temperatura = sensor.temperature()
        umidade = sensor.humidity()
        
        local_time_tuple = rtc.datetime()
        
        # VALIDAÇÃO CRÍTICA: Só envia dados se o ano for válido (após a sincronização).
        if local_time_tuple[0] > 2024:
            contagem += 1
            data_str = formatar_data(local_time_tuple)
            hora_str = formatar_hora(local_time_tuple)
            
            # Formato: Contagem;Dispositivo;Data;Hora;Temperatura;Umidade
            dados_csv = (
                f"{contagem};{ID_DISPOSITIVO};{data_str};{hora_str};"
                f"{temperatura:.2f};{umidade:.2f}"
            )
            
            print(dados_csv)
            exibir_oled_dados(temperatura, umidade, contagem)
            
            # --- LÓGICA DE SINCRONIZAÇÃO PERIÓDICA (Opcional) ---
            if utime.time() - ultima_sincronizacao > 3600:
                print("TRY_RESYNC") # Sinal para o laptop tentar a sincronização de novo
                ultima_sincronizacao = utime.time()
            # ----------------------------------------
            
        else:
            # Se o ano ainda estiver errado (e.g., 2021), avisa e não envia dados.
            exibir_oled(f"{ID_DISPLAY}", 0, limpar=True)
            exibir_oled("AGUARDANDO HORA...", 20)
            exibir_oled(f"T: {temperatura:.1f}C U: {umidade:.1f}%", 40)
            oled.show()
            # Envia um sinal de STATUS para evitar que o laptop trave na leitura
            print("WAITING_RTC")
            
        
    except OSError as e:
        exibir_oled("ERRO LEITURA DHT", 0, limpar=True)
        exibir_oled("Aguardando...", 10)
        print(f"ERRO: Leitura do sensor falhou: {e}")


# --- INICIALIZAÇÃO E LOOP PRINCIPAL ---
# Chama a função de sincronização
sync_success = sincronizar_rtc_serial()

exibir_oled("Coleta Iniciada", 40)
exibir_oled("Intervalo: 20s", 50)
utime.sleep(2) 

while True:
    coletar_e_enviar()
    utime.sleep(INTERVALO_LEITURA)
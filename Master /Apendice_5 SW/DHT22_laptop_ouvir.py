# Script Python para PC/Laptop
# Responsável por: Abrir a porta serial, sincronizar o RTC do Pico W e salvar dados em CSV.

import serial
import time
import os
from datetime import datetime

# Este é a segunda parte do programa. A primira parte roda no main.py do Raspberry e este em menos de 15 segundos deve rodar no prompt shell do Laptop na mesma porta COM
# --- CONFIGURAÇÕES ---
PORTA = 'COM4' # Verifique se esta é a porta correta
BAUD_RATE = 115200
ARQUIVO_DESTINO = r'C:\Mestrado_Unesp\RASP_DHT22.CSV'
TIMEOUT_SYNC = 15 # Segundos para esperar o sinal READY_TO_SYNC
# ---------------------

def inicializar_serial():
    """Tenta abrir a porta serial."""
    try:
        ser = serial.Serial(PORTA, BAUD_RATE, timeout=TIMEOUT_SYNC)
        # Espera um momento para a porta serial se estabilizar após a abertura
        time.sleep(2) 
        return ser
    except serial.SerialException as e:
        print(f"ERRO: Não foi possível abrir a porta {PORTA}. {e}")
        print("Certifique-se de que a porta não está sendo usada por outro programa (como o Thonny).")
        return None

def sincronizar_hora_pico(ser):
    """
    Envia a hora atual do PC para o Pico W após receber o sinal 'READY_TO_SYNC'.
    Retorna a string de data/hora que foi enviada.
    """
    print("\n--- INICIANDO SINCRONIZAÇÃO RTC ---")
    
    # Obtém a hora atual do PC e formata para o padrão esperado pelo Pico W
    now = datetime.now()
    # Formato: YYYY, MM, DD, weekday, HH, MM, SS (ex: 2025,10,5,6,11,10,0)
    # weekday: 0=Segunda, 6=Domingo. O Python usa 0=Segunda, o RTC usa 0=Segunda.
    weekday = now.weekday() 
    
    # Se o dia da semana for domingo (6 no Python), o MicroPython espera 6
    # Se for domingo, use 6 (domingo)
    # Se for de segunda a sábado (0 a 5), use o valor de now.weekday() + 1
    # MicroPython RTC espera: (ano, mês, dia, dia_da_semana, hora, minuto, segundo, microssegundo)
    # Dia da semana (0-6): 0=Seg, 1=Ter, ..., 5=Sáb, 6=Dom
    
    # Python weekday(): 0=Segunda, 6=Domingo
    # RTC de MicroPython usa o mesmo padrão (0 a 6)
    
    rtc_time_tuple = f"{now.year},{now.month},{now.day},{weekday},{now.hour},{now.minute},{now.second}"
    
    sync_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    # Loop de escuta para capturar o sinal READY_TO_SYNC
    start_time = time.time()
    while (time.time() - start_time) < TIMEOUT_SYNC + 15: # Dá mais tempo para o boot
        try:
            linha_bytes = ser.readline()
            if linha_bytes:
                linha = linha_bytes.decode('utf-8').strip()
                print(f"[SYNC MONITOR]: {linha}")

                if "READY_TO_SYNC" in linha:
                    print("[SYNC OK]: Sinal READY_TO_SYNC recebido.")
                    
                    # Envia o comando de hora
                    # NOVO FORMATO: Usa ':' como separador e '\r\n' para robustez serial.
                    comando = f"RTC_SET:{rtc_time_tuple}\r\n" 
                    print(f"Enviando hora: {sync_time_str}...")
                    ser.write(comando.encode('utf-8'))
                    
                    # Espera a confirmação do Pico W ou passa
                    time.sleep(0.5)
                    ser.flushInput() # Limpa o buffer para remover a confirmação e lixo

                    return sync_time_str
        except Exception as e:
            # Ignora erros de decodificação durante o boot
            pass 

    print("[ERRO SYNC]: Tempo limite esgotado. Pico W não enviou READY_TO_SYNC.")
    print("Certifique-se de que o Pico W está rodando o código MicroPython correto.")
    print("Continuando sem sincronização. A hora será o padrão 2021.")
    return None

def coletar_dados(ser, arquivo_destino, sync_time_str):
    """Lê continuamente os dados da serial e salva no CSV."""
    
    # Extrai Data e Hora separadas da string de sincronização para substituição
    sync_date_only = sync_time_str.split(' ')[0]
    sync_time_only = sync_time_str.split(' ')[1]
    
    # Verifica se o arquivo existe e cria o cabeçalho se não existir
    escrever_cabecalho = not os.path.exists(arquivo_destino) or os.path.getsize(arquivo_destino) == 0
    
    try:
        with open(arquivo_destino, 'a', newline='', encoding='utf-8') as f:
            
            if escrever_cabecalho:
                f.write("Contagem;Dispositivo;Data;Hora;Temperatura;Umidade\n")
                print(f"[ARQUIVO] Cabeçalho escrito em: {arquivo_destino}")

            print("Sincronização de hora enviada. Iniciando Coleta...")
            
            # Limpa o buffer de entrada uma última vez, caso o Pico W tenha enviado algo enquanto processava o RTC
            print("[COLETA] Limpando buffer de dados antigos (incluindo o '2021-01-01' antigo) antes de iniciar...")
            ser.flushInput()
            time.sleep(1) # Dá um pequeno tempo para o Pico W começar a rodar o loop principal

            while True:
                # O script do laptop não pode travar, então lê uma linha
                linha_bytes = ser.readline()
                if linha_bytes:
                    try:
                        linha = linha_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        continue # Ignora linhas mal-formadas

                    # --- TRATAMENTO DE STATUS E MONITORAMENTO ---
                    if "RTC_SET_SUCCESS" in linha:
                        print(f"[MONITOR]: {linha}")
                        continue
                    
                    # CRÍTICO: Se o Pico W está esperando o RTC estabilizar, ele envia esse sinal. O Laptop IGNORA (não salva).
                    if "WAITING_RTC" in linha:
                        print("[MONITOR]: Pico W está validando RTC. Ignorando leitura.")
                        continue

                    # Se a linha for um erro ou outra mensagem de status, apenas imprime no console.
                    if any(msg in linha for msg in ["ERRO", "SYNC MONITOR", "TRY_RESYNC"]):
                        print(f"[MONITOR]: {linha}")
                        continue
                    
                    # --- PROCESSAMENTO DE DADOS CSV ---
                    partes = linha.split(';')
                    
                    # Se for uma linha CSV válida (pelo menos 6 partes)
                    if len(partes) >= 6:
                        
                        # NOVIDADE CRÍTICA: CORREÇÃO DE DATA
                        data_lida = partes[2]
                        hora_lida = partes[3]

                        if sync_time_str and data_lida == "2021-01-01":
                            # Substitui a data antiga pela data real do PC
                            partes[2] = sync_date_only
                            
                            # Opção: Manter a hora lida ou usar a hora da sincronização
                            # Para a primeira coleta, é mais seguro usar a hora da sincronização para garantir a ordem correta.
                            # Para as coletas subsequentes com 2021, o Pico W as impedirá.
                            # Vamos corrigir o ano/mês/dia e manter a hora lida, se possível.

                            linha_corrigida = ';'.join(partes)
                            print(f"[CORRIGIDO]: {linha_corrigida}")
                            f.write(linha_corrigida + '\n')
                            print(f"[SALVO]: {partes[0]};{partes[1]};{sync_date_only};{hora_lida};{partes[4]};{partes[5]}")

                        # ATENÇÃO: A lógica abaixo estava incorreta (local_time_tuple[0] é variável de MicroPython, não existe aqui).
                        # A linha corrigida já garante a escrita.
                        # Para evitar erros de referência no Python do PC, vou simplificar esta parte.

                        # O Pico W só envia dados se a contagem for > 0.
                        elif partes[0].isdigit() and data_lida != "2021-01-01":
                            # Salva normalmente se a data já estiver correta (após a estabilização do RTC)
                            f.write(linha + '\n')
                            print(f"[SALVO]: {linha}")


    except KeyboardInterrupt:
        print("\nPrograma interrompido pelo usuário. Fechando conexão.")
    except Exception as e:
        print(f"\nOcorreu um erro durante a coleta: {e}")
    finally:
        ser.close()
        print("Conexão serial fechada.")

if __name__ == '__main__':
    print("*** INICIANDO O COLETOR SERIAL ***")
    print(f"Porta: {PORTA} | Destino: {ARQUIVO_DESTINO}")
    print("Certifique-se de que o Pico W foi reiniciado.")

    serial_conn = inicializar_serial()

    if serial_conn:
        # Tenta sincronizar. sync_time_str conterá a hora do PC ou None em caso de falha.
        time_data = sincronizar_hora_pico(serial_conn) 
        
        # Define um valor de fallback se a sincronização falhar, usando a hora de execução do script
        if not time_data:
            time_data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Inicia o loop de coleta de dados
        coletar_dados(serial_conn, ARQUIVO_DESTINO, time_data)
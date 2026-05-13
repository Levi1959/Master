import paho.mqtt.client as mqtt
import time
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

# --- Configurações de Limites ---
TEMP_MAX = 35.0
TEMP_MIN = 15.0
UMID_MAX = 100.0
UMID_MIN = 30.0

# --- Configurações MQTT ---
MQTT_SERVER = "192.168.15.14" 
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"

# Arquivos CSV
FILE_SD = "dados_estacao_SD.csv"
FILE_REMOTO = "dados_estacao_REMOTE.csv"

# Inicializa arquivos CSV com cabeçalho se não existirem
for f in [FILE_SD, FILE_REMOTO]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            file.write("leitura,data_hora,temp,umid,id_placa\n")

# --- MEMÓRIA RAM ---
MAX_POINTS = 50 

sd_leituras = deque(maxlen=MAX_POINTS)
sd_temps = deque(maxlen=MAX_POINTS)
sd_umids = deque(maxlen=MAX_POINTS)

re_leituras = deque(maxlen=MAX_POINTS)
re_temps = deque(maxlen=MAX_POINTS)
re_umids = deque(maxlen=MAX_POINTS)

# --- MQTT ---
# AQUI ESTÁ A CORREÇÃO: Agora tem 5 argumentos (incluindo properties)
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao Broker Local (Código: {reason_code})")
    # O "#" faz o Python bisbilhotar todas as mensagens do broker para descobrirmos o que os sensores estão a enviar
    client.subscribe("#")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        
        # --- LINHA ESPIÃ ---
        print(f"DEBUG -> Tópico: {msg.topic} | Mensagem: {payload}")
        
        dados = payload.split(',')
        
        if len(dados) >= 5:
            try:
                leitura = int(dados[0])
                temp = float(dados[2])
                umid = float(dados[3])
            except ValueError as ve:
                print(f"DEBUG -> Erro ao converter números: {ve}")
                return 
            
            id_placa = dados[4].strip()
            
            filename = FILE_SD if "SD_CARD" in id_placa else FILE_REMOTO
            with open(filename, "a") as f:
                f.write(payload + "\n")
            
            if "SD_CARD" in id_placa:
                sd_leituras.append(leitura)
                sd_temps.append(temp)
                sd_umids.append(umid)
            else:
                re_leituras.append(leitura)
                re_temps.append(temp)
                re_umids.append(umid)
                
            print(f"Dados Gravados [{id_placa}]: {payload}")
        else:
            print(f"DEBUG -> Mensagem ignorada (menos de 5 itens separados por vírgula): {payload}")
            
    except Exception as e:
        print(f"Erro no processamento MQTT: {e}")

# --- Configuração da Interface Gráfica ---
plt.style.use('ggplot')
fig, ((ax_temp_sd, ax_temp_re), (ax_umid_sd, ax_umid_re)) = plt.subplots(2, 2, figsize=(14, 9))
fig.canvas.manager.set_window_title('Monitoramento IoT - Estações Meteorológicas')

bbox_props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.85, edgecolor='#cccccc')

def atualizar_grafico(i):
    try:
        axes = [ax_temp_sd, ax_umid_sd, ax_temp_re, ax_umid_re]
        for ax in axes:
            ax.clear()
        
        if len(sd_leituras) > 0:
            leituras_plot = list(sd_leituras)[-15:]
            temps_plot = list(sd_temps)[-15:]
            umids_plot = list(sd_umids)[-15:]
            
            media_temp_sd = sum(list(sd_temps)[-2:]) / min(2, len(sd_temps))
            media_umid_sd = sum(list(sd_umids)[-2:]) / min(2, len(sd_umids))

            ax_temp_sd.plot(leituras_plot, temps_plot, label='Temp', color='#e31a1c', marker='o')
            ax_temp_sd.axhline(y=TEMP_MAX, color='red', linestyle='--', alpha=0.6, label=f'Max ({TEMP_MAX})')
            ax_temp_sd.axhline(y=TEMP_MIN, color='blue', linestyle='--', alpha=0.6, label=f'Min ({TEMP_MIN})')
            ax_temp_sd.text(0.03, 0.95, f"SD Card: Temperatura\nMédia: {media_temp_sd:.1f} °C", transform=ax_temp_sd.transAxes, fontsize=11, verticalalignment='top', bbox=bbox_props)

            ax_umid_sd.plot(leituras_plot, umids_plot, label='Umid', color='#1f78b4', marker='o')
            ax_umid_sd.axhline(y=UMID_MAX, color='darkblue', linestyle=':', alpha=0.6, label=f'Max ({UMID_MAX}%)')
            ax_umid_sd.axhline(y=UMID_MIN, color='orange', linestyle=':', alpha=0.6, label=f'Min ({UMID_MIN}%)')
            ax_umid_sd.text(0.03, 0.95, f"SD Card: Umidade\nMédia: {media_umid_sd:.1f} %", transform=ax_umid_sd.transAxes, fontsize=11, verticalalignment='top', bbox=bbox_props)

        if len(re_leituras) > 0:
            leituras_plot_re = list(re_leituras)[-15:]
            temps_plot_re = list(re_temps)[-15:]
            umids_plot_re = list(re_umids)[-15:]
            
            media_temp_re = sum(list(re_temps)[-10:]) / min(10, len(re_temps))
            media_umid_re = sum(list(re_umids)[-10:]) / min(10, len(re_umids))

            ax_temp_re.plot(leituras_plot_re, temps_plot_re, label='Temp', color='#ff7f00', marker='s')
            ax_temp_re.axhline(y=TEMP_MAX, color='red', linestyle='--', alpha=0.6, label=f'Max ({TEMP_MAX})')
            ax_temp_re.axhline(y=TEMP_MIN, color='blue', linestyle='--', alpha=0.6, label=f'Min ({TEMP_MIN})')
            ax_temp_re.text(0.03, 0.95, f"Remoto: Temperatura\nMédia: {media_temp_re:.1f} °C", transform=ax_temp_re.transAxes, fontsize=11, verticalalignment='top', bbox=bbox_props)

            ax_umid_re.plot(leituras_plot_re, umids_plot_re, label='Umid', color='#33a02c', marker='s')
            ax_umid_re.axhline(y=UMID_MAX, color='darkblue', linestyle=':', alpha=0.6, label=f'Max ({UMID_MAX}%)')
            ax_umid_re.axhline(y=UMID_MIN, color='orange', linestyle=':', alpha=0.6, label=f'Min ({UMID_MIN}%)')
            ax_umid_re.text(0.03, 0.95, f"Remoto: Umidade\nMédia: {media_umid_re:.1f} %", transform=ax_umid_re.transAxes, fontsize=11, verticalalignment='top', bbox=bbox_props)

        for ax in axes:
            ax.legend(loc='lower right', fontsize='x-small')
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Número da Leitura")

    except Exception as e:
        pass # Evita spam no ecrã se algo pequeno falhar no gráfico

# --- MQTT CLIENT ---
# Inicialização do cliente na versão mais nova
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start()
except:
    print("Não foi possível conectar ao Broker Local.")

print("Iniciando interface espiã...")

ani = FuncAnimation(fig, atualizar_grafico, interval=5000, cache_frame_data=False)
plt.subplots_adjust(left=0.05, right=0.97, top=0.95, bottom=0.08, wspace=0.15, hspace=0.25)

plt.show()
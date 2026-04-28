import paho.mqtt.client as mqtt
import time
import os

# Configurações MQTT
#MQTT_SERVER = "vcn-20250910-1351"  # O broker está na nuvem
MQTT_SERVER = "localhost"  # O broker está no mesmo Pi
MQTT_PORT = 1883
MQTT_USER = "user"
MQTT_PASSWORD = "senha"
TOPIC_MATO = "Mato_Temperatura_Local"
TOPIC_URBANO = "Urbano_Temperatura_Local"

# Nomes dos arquivos de saída
FILENAME_MATO = "Mato_Temperatura_local.txt"
FILENAME_URBANO = "Urbano_Temperatura_local.txt"

def on_connect(client, userdata, flags, rc):
    """
    Função chamada quando a conexão com o broker for estabelecida.
    Assina os dois tópicos de temperatura.
    """
    print("Conectado ao broker MQTT com código de resultado:", rc)
    client.subscribe(TOPIC_MATO)
    client.subscribe(TOPIC_URBANO)
    print(f"Assinado os tópicos: {TOPIC_MATO} e {TOPIC_URBANO}")

def on_message(client, userdata, msg):
    """
    Função chamada quando uma mensagem for recebida.
    Decodifica a mensagem e salva em um arquivo de texto.
    """
    try:
        # Decodifica a mensagem de bytes para string
        payload_str = msg.payload.decode('utf-8')
        
        # Adiciona o timestamp à leitura no formato de texto
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        linha_texto = f"[{timestamp}] {payload_str}\n"

        # Verifica o tópico e salva no arquivo correspondente
        if msg.topic == TOPIC_MATO:
            with open(FILENAME_MATO, "a") as file:
                file.write(linha_texto)
            print(f"Dados salvos em {FILENAME_MATO}: {linha_texto.strip()}")
        elif msg.topic == TOPIC_URBANO:
            with open(FILENAME_URBANO, "a") as file:
                file.write(linha_texto)
            print(f"Dados salvos em {FILENAME_URBANO}: {linha_texto.strip()}")
        else:
            print(f"Mensagem recebida de um tópico não esperado: {msg.topic}")
            
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# Criar o cliente MQTT
client = mqtt.Client()

# Definir as credenciais
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

# Atribuir as funções de callback
client.on_connect = on_connect
client.on_message = on_message

# Conectar ao broker
client.connect(MQTT_SERVER, MQTT_PORT, 60)

# Iniciar o loop de escuta.
client.loop_forever()
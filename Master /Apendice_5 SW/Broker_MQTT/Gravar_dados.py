import paho.mqtt.client as mqtt
import time
import json
import os

# Configurações MQTT
MQTT_SERVER = "localhost"  # O broker está no mesmo Pi
MQTT_PORT = 1883
MQTT_USER = "icts"
MQTT_PASSWORD = "icts"
TOPIC_MATO = "Mato_Temperatura"
TOPIC_URBANO = "Urbano_Temperatura"

# Nomes dos arquivos de saída
FILENAME_MATO = "Mato_Temperatura.json"
FILENAME_URBANO = "Urbano_Temperatura.json"

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
    Decodifica a mensagem e salva em um arquivo JSON.
    """
    try:
        # Decodifica a mensagem de bytes para string e converte para JSON
        payload_str = msg.payload.decode('utf-8')
        dados = json.loads(payload_str)
        
        # Adiciona o timestamp à leitura
        dados['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Converte o objeto de volta para uma string JSON
        json_line = json.dumps(dados) + '\n'

        # Verifica o tópico e salva no arquivo correspondente
        if msg.topic == TOPIC_MATO:
            with open(FILENAME_MATO, "a") as file:
                file.write(json_line)
            print(f"Dados salvos em {FILENAME_MATO}: {json_line.strip()}")
        elif msg.topic == TOPIC_URBANO:
            with open(FILENAME_URBANO, "a") as file:
                file.write(json_line)
            print(f"Dados salvos em {FILENAME_URBANO}: {json_line.strip()}")
        else:
            print(f"Mensagem recebida de um tópico não esperado: {msg.topic}")
            
    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON. Dados recebidos: {msg.payload}")
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
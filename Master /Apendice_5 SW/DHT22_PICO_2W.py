import machine
import dht
import time

# O pino que o DHT22 está conectado. Trocamos para GP0
dht_pin = machine.Pin(2)

# Cria uma instância do sensor DHT22
sensor_dht = dht.DHT22(dht_pin)

print("Iniciando o teste do sensor DHT22...")

# Adiciona um atraso de 2 segundos para o chip Wi-Fi se estabilizar
time.sleep(2)

try:
    while True:
        # Tenta ler os dados do sensor
        sensor_dht.measure()

        # Obtém os valores de temperatura e umidade
        temperatura = sensor_dht.temperature()
        umidade = sensor_dht.humidity()

        # Imprime os resultados no console do Thonny
        print("--------------------")
        print("Temperatura:", temperatura, "°C")
        print("Umidade:", umidade, "%")
        print("--------------------")

        # Aguarda 5 segundos antes da próxima leitura para evitar sobrecarga
        time.sleep(5)

except OSError as e:
    # Se ocorrer um erro, imprime a mensagem de erro
    print("Erro ao ler dados do sensor:", e)
import network
import time
    
SSID = "Eliete_2G"
PASSWORD = "senha01957"
    
print("Tentando conectar ao Wi-Fi...")
    
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
    
max_tries = 60
while not wlan.isconnected() and max_tries > 0:
    print("Aguardando conexão...")
    time.sleep(1)
    max_tries -= 1
        
if wlan.isconnected():
    print("Conectado! Configurações de rede:", wlan.ifconfig())
else:
    print("Falha na conexão Wi-Fi. Verifique a senha e o firmware.")
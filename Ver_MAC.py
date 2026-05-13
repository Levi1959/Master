import network
import binascii

# Ativa a interface de rede Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Obtém o endereço MAC e o converte para um formato legível
mac_address = binascii.hexlify(wlan.config('mac'),':').decode()

# Imprime o endereço MAC no shell do Thonny
print("O endereço MAC desta placa é:", mac_address)
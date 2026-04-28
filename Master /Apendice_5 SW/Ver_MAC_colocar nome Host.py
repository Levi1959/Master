import network
import binascii

# ---
# Variável para definir o novo nome de host. Altere esta linha!
# ---
novo_nome_host = "Pico W 2"

# Ativa a interface de rede Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Obtém o endereço MAC e o converte para um formato legível
mac_address = binascii.hexlify(wlan.config('mac'),':').decode()

# Imprime o endereço MAC
print("O endereço MAC desta placa é:", mac_address)
print("-" * 30)

# Obtém e imprime o nome de host ATUAL
hostname_atual = wlan.config('hostname')
if hostname_atual:
    print(f"O nome de host atual é: {hostname_atual}")
else:
    print("O nome de host ainda não está definido.")

# ---
# Trecho de código que altera o nome de host
# ---
print(f"\nAlterando o nome de host para: {novo_nome_host}...")
wlan.config(hostname=novo_nome_host)

# Obtém e imprime o NOVO nome de host para confirmar a alteração
hostname_novo = wlan.config('hostname')
print(f"O novo nome de host é: {hostname_novo}")
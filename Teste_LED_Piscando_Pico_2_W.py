from machine import Pin
from time import sleep

# Define o pino do LED integrado do Pico W
led = Pin("LED", Pin.OUT)

# Loop principal para piscar o LED
while True:
    print("Ligando o LED...")
    led.on()       # Liga o LED
    sleep(1)       # Espera 1 segundo
    
    print("Desligando o LED...")
    led.off()      # Desliga o LED
    sleep(1)       # Espera 1 segundo
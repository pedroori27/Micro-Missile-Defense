import serial
import serial.tools.list_ports
import time

arduino_porta = None # Define a variável arduino_porta como None

for porta in serial.tools.list_ports.comports(): # procura todas as portas seriais disponíveis
    print(porta.device, "-", porta.description) 

    if "Arduino" in porta.description: # Verifica se a descrição da porta contém Arduino, ai prova q a porta é do Arduino
        arduino_porta = porta.device
        break

if arduino_porta is None: # Caso não encontre a porta do arduino :(
    print("Arduino não encontrado.")
    exit()

arduino = serial.Serial(arduino_porta, 9600) # Aqui é onde a comunicação serial é iniciada com o Arduino, usando a porta encontrada e a taxa de transmissão de 9600 bps

time.sleep(10)  # Espera o Arduino reiniciar

while True:
    mensagem = arduino.readline().decode("utf-8").strip()
    print(mensagem)
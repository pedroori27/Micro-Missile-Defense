import serial
import serial.tools.list_ports
import time
search = serial.tools.list_ports.comports()
for port in search:
    print(port.device)
    print(port.description)
    print(port.hwid)
    print(port.vid)
    print(port.pid)
    print(port.serial_number)
    print(port.location)
    print(port.manufacturer)
    print(port.product)
    print(port.interface)
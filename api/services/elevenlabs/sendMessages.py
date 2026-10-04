from socket import *


def transferMessage(nativeMessage, translatedMessage):
    #Ip = 172.16.175.16
    # Port 5000
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(("172.16.175.16", 5000))

    #print(nativeMessage)
    #print(translatedMessage)

    grove_payload = f"SPEAK:{nativeMessage}\n"
    arduino_payload = f"ENGLISH:{translatedMessage}\n"

    sock.sendall(grove_payload.encode("utf-8"))
    sock.sendall(arduino_payload.encode("utf-8"))

    sock.close()
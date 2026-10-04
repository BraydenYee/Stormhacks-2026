from socket import *


def transferMessage(nativeMessage, translatedMessage):
    #Ip = 172.16.175.16
    # Port 5000
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(("127.0.0.1", 5000))

    sock.sendall(nativeMessage.encode("utf-8"))

    sock.sendall(translatedMessage.encode("utf-8"))

    sock.close()

    

transferMessage("Test", "test")




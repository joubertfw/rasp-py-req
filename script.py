import RPi.GPIO as GPIO
import json
import requests
from threading import Thread
import time
import datetime
import os
import socket
import lcddriver
import subprocess
import sqlite3

GPIO.setmode(GPIO.BCM)

conn = sqlite3.connect('raspSN.db')
cursor = conn.cursor()

lcd = lcddriver.lcd()
lcd.lcd_clear()

LED1_RED = 14
LED1_GREEN = 15
LED1_BLUE = 18

GPIO.setup(LED1_RED,GPIO.OUT)
GPIO.output(LED1_RED, 0)
GPIO.setup(LED1_GREEN,GPIO.OUT)
GPIO.output(LED1_GREEN, 0)
GPIO.setup(LED1_BLUE,GPIO.OUT)
GPIO.output(LED1_BLUE, 0)

with open('/home/pi/rasp-py-req/config.json', 'r') as f:
    jsonFile = json.load(f)
    config = jsonFile['CONFIG']
    status = jsonFile['STATUS']

code = -1
buffer = []
headers = {"APIkey" : config['SERVER_KEY'] }

def getMAC(interface=config['INTERFACE_NAME']):
    try:
        str = open(config['INTERFACE_FOLDER'] %interface).read()
    except Exception as e:
        print("Exception in function getMAC")
        print(e)
        str = "00:00:00:00:00:00"
    return str[0:17]

def getIP():
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
    except Exception as e:
        host_ip = "0.0.0.0"
        print("Exception in function getIP")
        print(e)
    return host_ip

def getSSID():
    try:
        ssid = str(subprocess.check_output(['iwgetid','-r']))
    except Exception as e:
        print("Exception in function getSSID")
        print(e)
        ssid = "........."
    return ssid[2:len(ssid)-3]

def showInfo():
    lcd.lcd_display(spaceText("VERSAO " + config['VERSION']))
    time.sleep(4.0)
    lcd.lcd_display(spaceText("IP " + getIP()), spaceText("MAC " + ''.join(getMAC().split(':'))))
    time.sleep(4.0)
    lcd.lcd_display(spaceText("HOST " + socket.gethostname()), spaceText("WIFI " + getSSID()))
    time.sleep(4.0)
    lcd.lcd_display(spaceText(config['SERVER_READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))

def shutdown():
    lcd.lcd_clear()
    GPIO.cleanup()
    lcd.lcd_display(spaceText("DESLIGANDO..."))
    time.sleep(1)
    lcd.lcd_clear()
    lcd.lcd_backlight("off")
    os.system("sudo shutdown -h now")

def changeRGBLed(r, g, b):
    GPIO.output(LED1_RED, r)
    GPIO.output(LED1_GREEN, g)
    GPIO.output(LED1_BLUE, b)

def spaceText(texto = ' '):
    return " " * int((16 - len(texto))/2) + texto

def changeDisplayLed(texto = ' '):
    if texto.count(' '):
        for i in reversed(range(0,len(texto))):
            if texto[i] == " ":
                lcd.lcd_display(spaceText(texto[:i]), spaceText(texto[i+1:len(texto)]))
                break
    else:
        lcd.lcd_display(spaceText(texto[:len(texto)]))

def ledStatusChange(ledCode = 0):
    try:
        changeDisplayLed(status[ledCode])
        if ledCode == 0:
            changeRGBLed(0, 1, 0)
        elif ledCode == 1:
            changeRGBLed(0, 0, 1)
        elif ledCode in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
            changeRGBLed(1, 0, 0)
    except Exception as e:
        print("Except in function ledStatusChange: ")
        print(e)

def insertDB(Serial1, Serial2 = None, Enviado = False, DataCad = datetime.datetime.now()):
    cursor.execute("INSERT INTO SerialNumbers (Serial1, Serial2, Enviado, DataCad) VALUES (?, ?, ?, ?);", (Serial1, Serial2, Enviado, DataCad))
    conn.commit()

def selectDB():
    dados = cursor.execute("SELECT * FROM SerialNumbers as (Id, Serial1, Serial2, Enviado, DataCad);")
    print(dados)
    print(type(dados))
    for linha in cursor.fetchall():
        print(linha)
        to_json = json.dumps(linha)
        print(to_json)


def sendBufferData():
    global buffer
    while (len(buffer) > 0):
        try:
            url = config['SERVER_URL'].format(config['SERVER_IP'], serialNumber, getMAC())
            resp = requests.post(url, headers = headers, timeout = 2)
        except:
            return False
        buffer.pop()
        print(buffer)
        time.sleep(2.0)
    return True

def sendInput(inputText, newSerieNumber = None):
    global buffer
    if (inputText == "@@MCMEXIT@@"):
         return False
    elif (inputText == "@@MCMSHUT@@"):
        shutdown()
    elif (inputText == "@@MCMINFO@@"):
        showInfo()
    else:
        sensorMAC = getMAC()
        lcd.lcd_display(spaceText(config['SERVER_PROCESSING']))
        if newSerieNumber == None:
            url = config['SERVER_URL'].format(config['SERVER_IP'], inputText, sensorMAC)
        else:
            url = config['SERVER_URL_BIND'].format(config['SERVER_IP'], inputText, newSerieNumber, sensorMAC)

        try:
            resp = requests.post(url, headers = headers, timeout = 2)
        except Exception as e:
            ledStatusChange()
            insertDB(Serial1 = inputText, Serial2 = newSerieNumber)
            print("Connection Exception")
            print(e)
        else:
            print("Servidor returned code " + str(resp.status_code))
            print('Success: ' + str(resp.text))
            jsonResp = json.loads(str(resp.text))
            resultCode = int(jsonResp["Resultado"])
            ledStatusChange(resultCode)

            if resultCode == 1:
                numeroSerieNovo = input()
                sendInput(inputText, numeroSerieNovo)
    return True

def verifyConnection():
    url = "http://" + config['SERVER_IP'] + "/MMHWebAPI/api/Produto?echo=ConnectionTest"
    global code
    global buffer
    codeAnterior = code
    while (True):
        if codeAnterior == -2 and code == -1:
            print("a")
            # lcd.lcd_display(spaceText(config['SERVER_READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))
            # sendBufferData()
        codeAnterior = code
        try:
            resp = requests.get(url, headers = headers, timeout = 2)
            resp.raise_for_status()
            if resp.status_code != 200:
                code = -2
                # lcd.lcd_display(spaceText(config['SERVER_DOWN']))
                changeRGBLed(1, 0, 0)
                time.sleep(2.0)
                changeRGBLed(0, 0, 0)
            else:
                code = -1
        except Exception as e:
            print(e)
            code = -2
            # lcd.lcd_display(spaceText(config['SERVER_NOCONN']))
            changeRGBLed(1, 0, 0)
            time.sleep(2.0)
            changeRGBLed(0, 0, 0)
        else:
            sendBufferData()
            # connThread = Thread(target=sendBufferData, args=[])
            # connThread.start()
        time.sleep(3.0)
        if code == -2:
            lcd.lcd_clear()

lcd.lcd_display(spaceText(config['SERVER_INITIALIZING']))
time.sleep(4)
lcd.lcd_display(spaceText(config['SERVER_READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))

connThread = Thread(target = verifyConnection, args = [], daemon = True)
connThread.start()

try:
    isRunning = True
    while (isRunning):
        numeroSerie = input()
        isRunning = sendInput(numeroSerie)
except Exception as e:
    print("Except in main code: ")
    print(e)
finally:
    conn.close()
    GPIO.cleanup()
    lcd.lcd_clear()
    lcd.lcd_backlight("off")
    os._exit(1)

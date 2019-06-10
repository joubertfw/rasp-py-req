import RPi.GPIO as GPIO
import json
import requests
from threading import Thread
import time
from datetime import datetime
import os
import socket
import lcddriver
import subprocess
import sqlite3

GPIO.setmode(GPIO.BCM)

conn = sqlite3.connect('/home/pi/rasp-py-req/raspSN.db')
cursor = conn.cursor()

lcd = lcddriver.lcd()
lcd.lcd_clear()

LED1_RED = 18
LED1_GREEN = 15
LED1_BLUE = 14

GPIO.setup(LED1_RED,GPIO.OUT)
GPIO.output(LED1_RED, 0)
GPIO.setup(LED1_GREEN,GPIO.OUT)
GPIO.output(LED1_GREEN, 0)
GPIO.setup(LED1_BLUE,GPIO.OUT)
GPIO.output(LED1_BLUE, 0)

with open('/home/pi/rasp-py-req/config.json', 'r') as f:
    jsonFile = json.load(f)
    config = jsonFile['CONFIG']
    server = jsonFile['SERVER']
    status = jsonFile['STATUS']

code = -1
headers = {"APIkey" : server['KEY'] }
tipo = ""

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

def setTime():
    url = server['TIME'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
    except Exception as e:
        print("Exception in getTime")
        print (e)
    else:
        jsonResp = json.loads(str(resp.text))
        currentDate = datetime.strptime(jsonResp[:len(jsonResp) - 7], '%Y-%m-%dT%H:%M:%S.%f')
        # os.system("sudo date -s \"{}\"".format(str(currentDate - resp.elapsed)))
        subprocess.check_call(["sudo", "date", "-s", str(currentDate - resp.elapsed)], stdout = subprocess.DEVNULL)

def getName():
    url = server['NAME'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
    except Exception as e:
        print("Exception in getName")
        print (e)
        return "Sensor"
    else:
        jsonResp = json.loads(str(resp.text))
        return jsonResp

def setType():
    global tipo
    url = server['TYPE'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
    except Exception as e:
        print("Exception in getType")
        print (e)
    else:
        tipo = json.loads(str(resp.text))

def showInfo():
    lcd.lcd_display(spaceText("VERSAO " + config['VERSION']), spaceText("NOME " + getName()))
    time.sleep(4.0)
    lcd.lcd_display(spaceText("IP " + getIP()), spaceText("MAC " + ''.join(getMAC().split(':'))))
    time.sleep(4.0)
    lcd.lcd_display(spaceText("HOST " + socket.gethostname()), spaceText("WIFI " + getSSID()))
    time.sleep(4.0)
    lcd.lcd_display(spaceText(config['READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))

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

def insertDB(NumeroSerie1, NumeroSerie2 = None, Data = datetime.now()):
    cursor.execute("INSERT INTO SerialNumbers (NumeroSerie1, NumeroSerie2, Data) VALUES (?, ?, ?);", (NumeroSerie1, NumeroSerie2, Data))
    conn.commit()

def selectDB():
    dados = cursor.execute("SELECT * FROM SerialNumbers as (Id, NumeroSerie1, NumeroSerie2,  Data);")
    print(dados)
    print(type(dados))
    for linha in cursor.fetchall():
        print(linha)
        to_json = json.dumps(linha)
        print(to_json)

def selectDBFormated():
    cursor.execute("SELECT * FROM SerialNumbers;")
    r = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
    print(r)

def sendBufferData():
    print("NADA")

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
        lcd.lcd_display(spaceText(config['PROCESSING']))
        if newSerieNumber == None:
            url = server['SEND'].format(server['IP'], inputText, sensorMAC)
        else:
            url = server['BIND'].format(server['IP'], inputText, newSerieNumber, sensorMAC)

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
                sendInput(inputText = inputText, newSerieNumber = numeroSerieNovo)
    return True

def verifyConnection():
    url = server['ECHO'].format(server['IP'])
    global code
    global buffer
    codeAnterior = code
    countConn = 0
    while (True):
        if codeAnterior == -2 and code == -1:
            print("Conectado 1")
            # sendBufferData()
        codeAnterior = code
        try:
            resp = requests.get(url, headers = headers, timeout = 2)
            resp.raise_for_status()
            if resp.status_code != 200:
                code = -2
                countConn += 1
            else:
                code = -1
        except Exception as e:
            print(e)
            code = -2
            countConn += 1
        else:
            print("Conectado 2")
            countConn = 0
            sendBufferData()
            # connThread = Thread(target=sendBufferData, args=[])
            # connThread.start()
        if countConn == 3:
            changeRGBLed(1, 0, 0)
            time.sleep(1.5)
            changeRGBLed(0, 0, 0)
            time.sleep(1.5)

lcd.lcd_display(spaceText(config['INITIALIZING']))
time.sleep(4)
lcd.lcd_display(spaceText(config['READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))

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

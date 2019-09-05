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
import random

GPIO.setmode(GPIO.BCM)

lcd = lcddriver.lcd()
lcd.lcd_clear()

LED1_RED = 23
LED1_GREEN = 22
LED1_BLUE = 17

LED2_RED = 5
LED2_GREEN = 25
LED2_BLUE = 24
BUZZER = 6

def criar(inicio, fim, prevar):
    prefixo = "243672419"
    size = len(prefixo) + len(prevar)
    num = str(random.randint(inicio, fim))
    num = prefixo + prevar[ : len(prevar) - len(num)] + num
    time.sleep(0.1)
    return(num[ : size])

GPIO.setup(LED1_RED,GPIO.OUT)
GPIO.output(LED1_RED, 0)
GPIO.setup(LED1_GREEN,GPIO.OUT)
GPIO.output(LED1_GREEN, 0)
GPIO.setup(LED1_BLUE,GPIO.OUT)
GPIO.output(LED1_BLUE, 0)

GPIO.setup(LED2_RED, GPIO.OUT)
GPIO.output(LED2_RED, 0)
GPIO.setup(LED2_GREEN, GPIO.OUT)
GPIO.output(LED2_GREEN, 0)
GPIO.setup(LED2_BLUE, GPIO.OUT)
GPIO.output(LED2_BLUE, 0)

GPIO.setup(BUZZER, GPIO.OUT)
GPIO.output(BUZZER, 0)

with open('/home/pi/rasp-py-req/config.json', 'r') as f:
    jsonFile = json.load(f)
    config = jsonFile['CONFIG']
    server = jsonFile['SERVER']
    status = jsonFile['STATUS']

offlineMode = False
sync = False
high = False
stat = "0"
headers = {"APIkey" : server['KEY'] }
typeRasp = ""

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
    print("SET TIME")
    url = server['TIME'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
        jsonResp = json.loads(str(resp.text))
    except Exception as e:
        print("Exception in getTime")
        print (e)
        return 100, resp
    else:
        currentDate = datetime.strptime(jsonResp[:len(jsonResp) - 7], '%Y-%m-%dT%H:%M:%S.%f')
        # print(currentDate)
        # os.system("sudo date -s \"{}\"".format(str(currentDate - resp.elapsed)))
        subprocess.check_call(["sudo", "date", "-s", str(currentDate - resp.elapsed)], stdout = subprocess.DEVNULL)
        return 0, resp

def getName():
    url = server['NAME'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
        jsonResp = json.loads(str(resp.text))
    except Exception as e:
        print("Exception in getName")
        print (e)
        return "Sensor"
    else:
        return jsonResp

def getStatus():
    url = server['STAT'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
        jsonResp = json.loads(str(resp.text))
    except Exception as e:
        print("Exception in getStatus")
        print(e)
        return("0")
    else:
        return jsonResp

def dbExecute(querry):
    conn = sqlite3.connect('/home/pi/rasp-py-req/raspSN.db')
    cursor = conn.cursor()
    cursor.execute(querry)
    dados = cursor.fetchall()
    conn.commit()
    conn.close()
    return dados

def setType():
    url = server['TYPE'].format(server['IP'], getMAC())
    try:
        resp = requests.get(url, headers = headers)
        tipo = json.loads(str(resp.text))
    except Exception as e:
        print("Exception in setType")
        print (e)
    else:
        if dbExecute("SELECT * FROM TipoRasp"):
            dbExecute("UPDATE TipoRasp SET Tipo = '{}';".format(tipo))
        else:
            dbExecute("INSERT INTO TipoRasp (Tipo) VALUES ('{}');".format(tipo))

def getType():
    global typeRasp
    if typeRasp == "":
        try:
            conn = sqlite3.connect('/home/pi/rasp-py-req/raspSN.db')
            cursor = conn.cursor()
            dados = cursor.execute("SELECT Tipo FROM TipoRasp;")
            data = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
            typeRasp = data[0]['Tipo']
            conn.close()
        except Exception as e:
            print("Exception in getType")
            print(Exception)
    return typeRasp

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

def turnBuzzer():
    if(high):
        GPIO.output(BUZZER, 1)
    time.sleep(0.3)
    GPIO.output(BUZZER, 0)

def changeRGBLed(r, g, b):
    GPIO.output(LED1_RED, r)
    GPIO.output(LED1_GREEN, g)
    GPIO.output(LED1_BLUE, b)
    # turnBuzzer()

def changeRGBLed2(r, g, b):
    GPIO.output(LED2_RED, r)
    GPIO.output(LED2_GREEN, g)
    GPIO.output(LED2_BLUE, b)

def blink(r, g, b, led = 1):
    if led is 1:
        changeRGBLed(0, 0, 0)
        time.sleep(1.0)
        changeRGBLed(r, g, b)
    else:
        changeRGBLed2(0, 0, 0)
        time.sleep(1.0)
        changeRGBLed2(r, g, b)
    time.sleep(1.0)

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
    changeRGBLed(0, 0, 0)
    time.sleep(0.02)
    try:
        changeDisplayLed(status[ledCode])
        if ledCode == 0 or ledCode == 11:
            changeRGBLed(0, 1, 0)
        elif ledCode == 1:
            changeRGBLed(0, 0, 1)
        elif ledCode in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
            changeRGBLed(1, 0, 0)
    except Exception as e:
        print("Except in function ledStatusChange: ")
        print(e)

def inputOffline(serialNumber1):
    sensorMAC = getMAC()
    tp = getType()
    url = server['SEND'].format(server['IP'], serialNumber1, sensorMAC)
    print("INPUT OFFLINE")
    if tp == "AMARR":
        ledStatusChange(ledCode = 1)
        #serialNumber2 = input()
        serialNumber2 = criar(0, 3333, "000000")
        print("{} -> {}".format(serialNumber1, serialNumber2))
    else:
        serialNumber2 = None

    if stat is 2:
        try:
            if tp == "AMARR":
                url = server['BIND'].format(server['IP'], serialNumber1, serialNumber2, sensorMAC)
            resp = requests.post(url, headers = headers, timeout = 10)
            jsonResp = json.loads(str(resp.text))
            resultCode = int(jsonResp["Resultado"])
            print("ResultCode: {}".format(resultCode))
            if resultCode in [6, 8]:
                dbExecute("INSERT INTO SerialNumbers (NumeroSerie1, NumeroSerie2, Data) VALUES ('{}', '{}', '{}');".format(serialNumber1, serialNumber2, datetime.now()))
                ledStatusChange(ledCode = 11)
            else:
                ledStatusChange(resultCode)
        except Exception as e:
            print(e)
    else:
        dbExecute("INSERT INTO SerialNumbers (NumeroSerie1, NumeroSerie2, Data) VALUES ('{}', '{}', '{}');".format(serialNumber1, serialNumber2, datetime.now()))
        ledStatusChange(ledCode = 11)

def selectDBFormated():
    conn = sqlite3.connect('/home/pi/rasp-py-req/raspSN.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM SerialNumbers;")
    data = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
    print(data)
    conn.close()
    return data

def sendBuffer():
    print("SINCRONIZANDO")
    url = server['SYNC'].format(server['IP'], getMAC())
    try:
        resp = requests.post(url, headers = headers, timeout = None, json = selectDBFormated())
    except Exception as e:
        print(e)
    else:
        print(resp.elapsed)
        dbExecute("DELETE FROM SerialNumbers;")

def inputOnline(serialNumber1, serialNumber2 = None):
    sensorMAC = getMAC()
    lcd.lcd_display(spaceText(config['PROCESSING']))
    if serialNumber2 == None:
        url = server['SEND'].format(server['IP'], serialNumber1, sensorMAC)
    else:
        print("{} -> {}".format(serialNumber1, serialNumber2))
        url = server['BIND'].format(server['IP'], serialNumber1, serialNumber2, sensorMAC)
    try:
        resp = requests.post(url, headers = headers, timeout = 10)
        if resp.status_code != 200:
            lcd.lcd_display(spaceText(config['TRYAGAIN']))
        else:
            jsonResp = json.loads(str(resp.text))
            resultCode = int(jsonResp["Resultado"])
            ledStatusChange(resultCode)
            if resultCode == 1:
                serialNumber2 = criar(0, 3333, "000000")
                #serialNumber2 = input()
                inputOnline(serialNumber1 = serialNumber1, serialNumber2 = serialNumber2)
    except Exception as e:
        print("Connection Exception")
        print(e)
        lcd.lcd_display(spaceText(config['TRYAGAIN']))

def sendInput():
    global offlineMode
    global high
    aux = criar(333333, 336666, "000000")
    inputText = aux
    print("\n" + aux)
    #inputText = input()
    turnBuzzer()
    if sync == True:
        lcd.lcd_display(spaceText(config['SYNCING']))
    elif (inputText == "@@MCMEXIT@@"):
         return False
    elif (inputText == "@@MCMSHUT@@"):
        shutdown()
    elif (inputText == "@@MCMINFO@@"):
        showInfo()
    elif (inputText == "@@MCMVOL@@"):
        high = not high
    else:
        if offlineMode == True:
            inputOffline(serialNumber1 = inputText)
        else:
            inputOnline(serialNumber1 = inputText)
    return True

def verifyConnection():
    url = server['ECHO'].format(server['IP'])
    global offlineMode
    global sync
    global stat
    hasOffline = offlineMode
    countConn = countTime = 0
    changeRGBLed2(0, 0, 1)

    while (True):
        print("offlineMode: {}".format(offlineMode))
        print("sync: {}".format(sync))
        print("stat: {}".format(stat))
        if hasOffline == True and offlineMode == False:
            lcd.lcd_display(spaceText(config['SYNCING']))
            sync = True
            sendBuffer()
            sync = False
            lcd.lcd_display(spaceText(config['READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))
        hasOffline = offlineMode
        try:
            stat = int(getStatus())
            if countTime >= 30:
                countTime, resp = setTime()
            else:
                resp = requests.get(url, headers = headers, timeout = 5)
                countTime += 1
            resp.raise_for_status()
            if resp.status_code != 200:
                countConn += 1
        except Exception as e:
            print(e)
            countConn += 1
        else:
            if stat is 1:
                lcd.lcd_display(spaceText(config['SYNCING']))
                sync = True
                sendBuffer()
                sync = False
                lcd.lcd_display(spaceText(config['READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))
            if stat is not 2:
                # print("Conectado")
                countConn = 0
                offlineMode = False
                changeRGBLed2(0, 0, 1)
        if countConn >= 3:
            offlineMode = True
            blink(1, 0, 0, led = 2)
            blink(1, 0, 0, led = 2)
        elif stat is 2:
            offlineMode = True
            blink(0, 0, 1, led = 2)
            blink(0, 0, 1, led = 2)
        else:
            time.sleep(2.5)

lcd.lcd_display(spaceText(config['INITIALIZING']))
setType()
time.sleep(4)
lcd.lcd_display(spaceText(config['READY'] + ": " + ''.join(getMAC().split(':'))), spaceText(getIP()))

connThread = Thread(target = verifyConnection, args = [], daemon = True)
connThread.start()

try:
    isRunning = True
    while (isRunning):
        isRunning = sendInput()
except Exception as e:
    print("Except in main code: ")
    print(e)
finally:
    GPIO.cleanup()
    lcd.lcd_clear()
    lcd.lcd_backlight("off")
    os._exit(1)

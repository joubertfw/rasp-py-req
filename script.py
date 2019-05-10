import RPi.GPIO as GPIO
import json
import requests
from threading import Thread
import time
import os
import lcddriver

GPIO.setmode(GPIO.BCM)

lcd = lcddriver.lcd()
lcd.lcd_clear()

#LED 1
LED1_RED = 13
LED1_GREEN = 19
LED1_BLUE = 26

GPIO.setup(LED1_RED,GPIO.OUT)
GPIO.output(LED1_RED, 0)
GPIO.setup(LED1_GREEN,GPIO.OUT)
GPIO.output(LED1_GREEN, 0)
GPIO.setup(LED1_BLUE,GPIO.OUT)
GPIO.output(LED1_BLUE, 0)

#Leitura de arquivos
arqIn = open(os.getcwd() + "/status", "r")
status = arqIn.readlines()

arqIn = open(os.getcwd() + "/config", "r")
config = arqIn.read().splitlines()

appUrl = config[0]
APIKEY = config[1]
PRONTO = config[2]
PROCESS = config[3]
S_SERV = config[4]
S_REDE = config[5]
INICIA = config[6]
TENTE_NOV = config[7]

code = -1
    
def getMAC(interface='wlan0'):
    # Retorna o endereço MAC da interface especifica
    try:
        str = open('/sys/class/net/%s/address' %interface).read()
    except:
        str = "00:00:00:00:00:00"
    return str[0:17]

def changeRGBLed(r, g, b):
    GPIO.output(LED1_RED, r)
    GPIO.output(LED1_GREEN, g)
    GPIO.output(LED1_BLUE, b)

def verifyConnection():    
    url = "http://" + appUrl + "/MMHWebAPI/api/Produto?echo=ConnectionTest"
    headers = {"APIkey" : APIKEY }
    global code    
    codeAnterior = code
    while (True):  
        print(code)
        print(url)
        if codeAnterior == -2 and code == -1:
            lcd.lcd_display(spaceText(PRONTO), spaceText(''.join(getMAC().split(':'))))                        
        codeAnterior = code
        try:
            resp = requests.get(url, headers = headers, timeout = 1)
            resp.raise_for_status()
            
            if resp.status_code != 200:
                code = -2                
                lcd.lcd_display(spaceText(S_SERV))
                changeRGBLed(1, 0, 0)
                time.sleep(1.0)
                changeRGBLed(0, 0, 0)
            else:                
                code = -1
        except:
            code = -2
            lcd.lcd_display(spaceText(S_REDE))
            changeRGBLed(1, 0, 0)
            time.sleep(1.0)
            changeRGBLed(0, 0, 0)                    
        time.sleep(2.0)
        if code == -2:
            lcd.lcd_clear()
   
def spaceText(texto):
    return " " * int((16 - len(texto))/2) + texto
   
def changeDisplayLed(texto):   
    if texto.count(' '):
        for i in reversed(range(0,16)):
            if texto[i] == " ":
                lcd.lcd_display(spaceText(texto[:i]), spaceText(texto[i+1:len(texto)-1]))                
                break
    else:
        lcd.lcd_display(spaceText(texto[:len(texto)-1]))

def ledStatusChange(ledCode):    
    try:
        changeDisplayLed(status[ledCode])
        if ledCode == 0:
            changeRGBLed(0, 1, 0)
        elif ledCode == 1:
            changeRGBLed(0, 0, 1)
        elif ledCode in [2, 3, 4, 5, 6, 7, 8, 9, 10]:             
            changeRGBLed(1, 0, 0)                      
    except:
        print("EXCEPT ledStatusChange")

headers = {"APIkey" : APIKEY }

lcd.lcd_display(spaceText(INICIA))
time.sleep(5)
lcd.lcd_display(spaceText(PRONTO), spaceText(''.join(getMAC().split(':'))))

connThread = Thread(target=verifyConnection, args=[])
connThread.start()

try:
    while (True):        
        numeroSerie = input()        
        changeRGBLed(0, 0, 0)
        sensorMAC = getMAC()
        url = "http://"+ appUrl + "/MMHWebAPI/api/Produto?numeroSerie=" + numeroSerie + "&sensorMAC=" + sensorMAC
        
        if code != -2:        
            lcd.lcd_display(spaceText(PROCESS))
            
            try:
                resp = requests.post(url, headers = headers, timeout = 10)
            except requests.exceptions.Timeout:
                code = -3
                changeRGBLed(1, 0, 0)
                lcd.lcd_display(spaceText(TENTE_NOV))                
            except:
                code = -2

            if resp.status_code != 200 or code == -2:
                print("AQUI")               
                print(code)
                print(resp.status_code)
            else:
                print('Success: ' + str(resp.text))
                print(resp.status_code)
                jsonResp = json.loads(str(resp.text))    
                print(jsonResp["Resultado"])
                resultCode = int(jsonResp["Resultado"])
                # code = resultCode
                ledStatusChange(resultCode)
                if resultCode == 1: 
                    # Necessita amarração
                    numeroSerieNovo = input()
                    url = "http://" + appUrl + "/MMHWebAPI/api/Produto?numeroSerie=" + numeroSerie + "&numeroSerieNovo=" + numeroSerieNovo + "&sensorMAC=" + sensorMAC
                    resp = requests.post(url, headers = headers)
                    if resp.status_code != 200:
                        code = -1
                    else:
                        jsonResp = json.loads(str(resp.text))    
                        print(jsonResp["Resultado"])
                        resultCode = int(jsonResp["Resultado"])
                        # code = resultCode
                        ledStatusChange(resultCode)
except:
    print("EXCEPT main")
finally:
    GPIO.cleanup()
    lcd.lcd_clear()
    lcd.lcd_backlight("off")

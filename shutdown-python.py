#!/usr/bin/env python
#
import RPi.GPIO as GPIO
import time
import os
import lcddriver

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN,pull_up_down=GPIO.PUD_UP)

lcd = lcddriver.lcd()

def spaceText(texto = ' '):
    return " " * int((16 - len(texto))/2) + texto

while True:
    #print GPIO.input(17) 
    if(GPIO.input(17) == False):
        lcd.lcd_clear()
        lcd.lcd_display(spaceText("DESLIGANDO..."))        
        GPIO.cleanup()
        time.sleep(1)
        lcd.lcd_clear()
        lcd.lcd_backlight("off")
        os.system("sudo shutdown -h now")
        break
    time.sleep(3)

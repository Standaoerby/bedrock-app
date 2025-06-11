import RPi.GPIO as GPIO
import time

BUTTON_PINS = [23, 24]

GPIO.setmode(GPIO.BCM)
for pin in BUTTON_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Кнопка замыкает на GND

try:
    print("Жми кнопки на GPIO 23 и 24 (Ctrl+C для выхода)")
    while True:
        for pin in BUTTON_PINS:
            if GPIO.input(pin) == GPIO.LOW:
                print(f"Кнопка на GPIO {pin} НАЖАТА")
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()

import requests
import time
import threading
import paho.mqtt.client as mqtt
import json
from io import BytesIO
from Logging import sendLogMessages, sendFinishPicture
from datetime import datetime

octoprint_ip = "127.0.0.1"
port = 5000
shelly_ip = "192.168.188.91"
broker_address = "127.0.0.1"
client = mqtt.Client("PCClient", transport="tcp")
file_url = f"http://{octoprint_ip}/downloads/logs/auth.log"
headers = {"X-Api-Key": "4E1BD42388C544499671AB3A5C83E5D6"}

thread_created = False
IsLightOn = False
IsLightOff = False
IsFirstShellyToggle = True
job_info = None

def program():
    global thread_created

    if not thread_created:
        threading.Thread(target=TurnLightOnOff).start()
        threading.Thread(target=createInfoList).start()
        sendLogMessages("Server wurde erfolgreich neu gestartet!")
        print("ThreadCreated")
        thread_created = True

    while True:
        try:
            file_content = download_and_read_file()
            UserLoggedIn = IsUserLoggedIn(file_content)
            turnOn3dprinter(UserLoggedIn)
        except Exception as e:
            sendLogMessages(f"Fehler: {e}")
            time.sleep(100)

def TurnLightOnOff():
    global IsLightOn
    global IsLightOff

    while True:
        try:
            file_content = download_and_read_file()
            UserLoggedIn = IsUserLoggedIn(file_content)

            if UserLoggedIn and not IsLightOn:
                publish_message("true","your_topic")
                IsLightOn = True
                IsLightOff = False
            elif not UserLoggedIn and not IsLightOff:
                publish_message("false","your_topic")
                IsLightOff = True
                IsLightOn = False

            time.sleep(10)
        except Exception as e:
            sendLogMessages(f"Fehler: {e}")
            time.sleep(100)

def publish_message(message,topic):
    try:
        client.connect(broker_address, 1883, 60)
        client.loop_start()
        client.publish(topic, message)
        client.loop_stop()
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)

def download_and_read_file():
    try:
        response = requests.get(file_url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{file_url}")
        time.sleep(100)
        return None

def IsUserLoggedIn(logs):
    try:
        last_message = logs.strip().split('\n')[-1]
        if "Logging in" in last_message:
            return True
        elif "Logging out" in last_message:
            return False
        else:
            return None
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)
        return None

def turnOn3dprinter(IsUserLoggedIn):
    try:
        if IsUserLoggedIn is not None:
            if IsUserLoggedIn:
                if not boolisPrinterConnected():
                    toggle_shelly()
                    isPrinterConnected()
                else:
                    isPrinterConnected()
            else:
                time.sleep(10)
        else:
            time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)

def toggle_shelly():
    url = f"http://{shelly_ip}/relay/0?turn=toggle"

    try:
        if not boolisPrinterConnected():
            response = requests.get(url)
            if response.status_code == 200:
                sendLogMessages("Drucker wurde angeschaltet")
                time.sleep(10)
            else:
                sendLogMessages("Fehler beim Umschalten des Shelly 1.")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{url}")
        time.sleep(100)

def isPrinterConnected():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            connection_data = response.json()
            if connection_data["current"]["state"] in ["Operational", "Printing"]:
                waitOnJob()
            else:
                tryConnectPrinter()
        else:
            sendLogMessages(f"Fehler bei {api_endpoint}")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def boolisPrinterConnected():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            connection_data = response.json()
            return connection_data["current"]["state"] in ["Operational", "Printing"]
        else:
            return False
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        return False

def tryConnectPrinter():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        data = {
            "port": "AUTO",
            "baudrate": 0,
            "printerProfile": "_default",
            "autoconnect": True,
            "command": "connect"
        }
        headers = {
            "X-Api-Key": "4E1BD42388C544499671AB3A5C83E5D6",
            "Content-Type": "application/json"
        }

        response = requests.post(api_endpoint, json=data, headers=headers)
        if response.status_code == 204:
            isPrinterConnected()
        else:
            sendLogMessages(f"Fehler: {response.status_code} bei {api_endpoint}")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def waitOnJob():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
        while True:
            response = requests.get(api_endpoint, headers=headers)
            if response.status_code == 200:
                job_info = response.json()
                if job_info.get("state") == "Printing":
                    sendLogMessages("Der Drucker ist am Drucken")
                    Fileavailable()
                    waitOnPrint()
                    break
                elif job_info.get("state") == "Operational":
                    time.sleep(10)
            else:
                sendLogMessages(f"Fehler beim Auslesen vom Job,{api_endpoint}")
                time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def IsPrinterPrinting():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
            response = requests.get(api_endpoint, headers=headers)
            if response.status_code == 200:
                job_info = response.json()
                if job_info.get("state") == "Printing":
                  return True
                else:
                    return False
            else:
                sendLogMessages(f"Fehler beim Auslesen vom Job,{api_endpoint}")
                time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def TurnOffShelly():
    url = f"http://{shelly_ip}/relay/0?turn=toggle"
    try:
        response = requests.get(url)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{url}")
        time.sleep(100)

def waitOnPrint():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
        while True:
            response = requests.get(api_endpoint, headers=headers)
            if response.status_code == 200:
                job_info = response.json()
                actprintSize = job_info.get("progress", {}).get("completion")
                if actprintSize == 100:
                    sendLogMessages("Der Druck ist fertig")
                    sendFinishedPrint()
                    TurnOffPrinter()
                    break
                elif actprintSize < 100:
                    time.sleep(50)
            else:
                sendLogMessages(f"Fehler beim Auslesen vom Job,{api_endpoint}")
                time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def TurnOffPrinter():
    api_endpoint = f"http://{octoprint_ip}/api/printer/tool"
    try:
        while True:
            response = requests.get(api_endpoint, headers=headers)
            if response.status_code == 200:
                job_info = response.json()
                temp = job_info.get("tool0", {}).get("actual")
                if temp <= 40:
                    sendLogMessages("Drucker wird jetzt ausgeschaltet")
                    deleteJob()
                    TurnOffShelly()
                    break
                else:
                    if isNewFileavailable() or IsPrinterPrinting():
                        waitOnJob()
                    else:
                        time.sleep(10)
            else:
                sendLogMessages(f"Fehler beim Abrufen der Druckertemperatur,{api_endpoint}")
                time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def Fileavailable():
    api_endpoint = f"http://{octoprint_ip}/api/files"
    global job_info
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            job_info = response.json()
        else:
            sendLogMessages(f"Fehler: {response.status_code} bei {api_endpoint}")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)

def isNewFileavailable():
    api_endpoint = f"http://{octoprint_ip}/api/files"
    global job_info
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            new_job_info = response.json()

            if job_info is None:
                job_info = new_job_info
                return False

            if isinstance(job_info, str):
                job_info = json.loads(job_info)

            new_files = new_job_info.get('files', [])
            new_hashes = {file['hash'] for file in new_files}

            old_files = job_info.get('files', [])
            old_hashes = {file['hash'] for file in old_files}

            if not old_hashes.issuperset(new_hashes):
                job_info = new_job_info
                return True

        return False
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        return False

def capture_screenshot(stream_url):
    response = requests.get(stream_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"Failed to capture image from stream. Status code: {response.status_code}")

def sendFinishedPrint():
    stream_url = f'http://{octoprint_ip}/webcam/?action=snapshot'
    try:
        TurnLightOnOffScreenshot(True)
        time.sleep(10)
        image = capture_screenshot(stream_url)
        if not IsUserLoggedIn(download_and_read_file()):
            TurnLightOnOffScreenshot(False)
        sendFinishPicture(image)
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")

def TurnLightOnOffScreenshot(Light):
    try:
        if Light:
            publish_message("true","your_topic")
        else:
            publish_message("false","your_topic")
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)

def deleteJob():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
        data = {
            "command": "cancel"
        }
        headers = {
            "X-Api-Key": "4E1BD42388C544499671AB3A5C83E5D6",
            "Content-Type": "application/json"
        }

        response = requests.post(api_endpoint, json=data, headers=headers)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)


def createInfoList():
    while True:
        if boolisPrinterConnected():
            jobInfo = f"http://{octoprint_ip}/api/job"
            printerInfo = f"http://{octoprint_ip}/api/printer"
            formatted_time = datetime.now()
            clock = formatted_time.strftime("%H:%M")

            try:
                response = requests.get(jobInfo, headers=headers)
                responsePrinter = requests.get(printerInfo, headers=headers)

                if response.status_code == 200 and responsePrinter.status_code == 200:
                    job_info = response.json()
                    printer_info = responsePrinter.json()

                    if job_info is None or printer_info is None:
                        sendLogMessages("Received None response from API")
                        time.sleep(10)
                        continue

                    # Extrahiere die gewünschten Werte aus job_info
                    file_name = job_info['job']['file'].get('name', 'N/A')
                    estimated_print_time = job_info['job'].get('estimatedPrintTime', 'N/A')
                    filament_length_cm = job_info['job']['filament'].get('tool0', {}).get('length', 'N/A')
                    if filament_length_cm != 'N/A':
                        try:
                            filament_length_m = round(float(filament_length_cm) / 1000, 3)
                        except ValueError:
                            filament_length_m = 'Ungültige Länge'
                    else:
                        filament_length_m = 'N/A'
                    completion = job_info['progress'].get('completion', 'N/A')
                    print_time_left = job_info['progress'].get('printTimeLeft', 'N/A')

                    # Extrahiere die gewünschten Werte aus printer_info
                    bed_actual = printer_info['temperature']['bed'].get('actual', 'N/A')
                    tool0_actual = printer_info['temperature']['tool0'].get('actual', 'N/A')

                    # Konvertiere die Werte in Strings
                    file_name_str = str(file_name)
                    estimated_print_time_str = format_time(estimated_print_time)
                    completion_str = str(completion)
                    print_time_left_str = format_time(print_time_left)
                    bed_actual_str = str(bed_actual)
                    tool0_actual_str = str(tool0_actual)

                    test = f"{file_name_str};{estimated_print_time_str};{completion_str};{print_time_left_str};{bed_actual_str};{tool0_actual_str};{filament_length_m};{clock}"
                    publish_message(test, "info")
                    time.sleep(1)

                else:
                    sendLogMessages(f"Fehler beim Auslesen der Daten, Job: {response.status_code}, Printer: {responsePrinter.status_code}")
                    time.sleep(10)
            except Exception as e:
                sendLogMessages(f"Exception: {e}")
                time.sleep(10)


def format_time(seconds):
    if(seconds is None):
        return ""
    try:
        seconds = int(seconds)  # Sicherstellen, dass seconds ein Integer ist
    except ValueError:
        return "Ungültige Zeit"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}:{minutes}"
    else:
        return f"{minutes} Min"

program()
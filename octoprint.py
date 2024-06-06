import requests
import time
import threading
import paho.mqtt.client as mqtt
import json
from io import BytesIO
from Logging import sendLogMessages, sendFinishPicture

# IP-Adresse des OctoPrint-Servers
octoprint_ip = "127.0.0.1"
port = 5000

shelly_ip = "192.168.188.91"

broker_address = "127.0.0.1"  # IP-Adresse des Raspberry Pi
client = mqtt.Client("PCClient", transport="tcp")

file_url = f"http://{octoprint_ip}/downloads/logs/auth.log"

headers = {
    "X-Api-Key": "4E1BD42388C544499671AB3A5C83E5D6"  # Dein API-Schlüssel hier
}

thread_created = False
IsLightOn = False
IsLightOff = False
IsFirstShellyToggle = True

job_info = None

def program():
    try:
        global thread_created

        if not thread_created:
            threading.Thread(target=TurnLightOnOff).start()
            sendLogMessages("Server wurde erfolgreich neu gestartet!")
            print("ThreadCreated")
            thread_created = True

        file_content = download_and_read_file()
        UserLoggedIn = IsUserLoggedIn(file_content)
        Is3dprinterOn = turnOn3dprinter(UserLoggedIn)
        time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)
        program()

def TurnLightOnOff():
    try:
        global IsLightOn
        global IsLightOff
        while True:
            file_content = download_and_read_file()
            UserLoggedIn = IsUserLoggedIn(file_content)

            if UserLoggedIn and not IsLightOn:
                publish_message("true")
                IsLightOn = True
                IsLightOff = False
            elif not UserLoggedIn and not IsLightOff:
                publish_message("false")
                IsLightOff = True
                IsLightOn = False
            time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)


def publish_message(message):
    try:
        client.connect(broker_address, 1883, 60)
        client.loop_start()
        topic = "your_topic"
        client.publish(topic, message)
        client.loop_stop()
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)
        program()

def download_and_read_file():
    try:
        response = requests.get(file_url, headers=headers)
        if response.status_code == 200:
            file_content = response.text
            return file_content
        else:
            return None
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{file_url}")
        time.sleep(100)
        program()

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
        program()



def turnOn3dprinter(IsUserLoggedIn):
    try:
        if IsUserLoggedIn is not None:
            if IsUserLoggedIn:
                if not boolisPrinterConnected():
                    toggle_shelly()
                else:
                    isPrinterConnected()
            else:
                time.sleep(10)
                program()
        else:
            program()
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)
        program()

def toggle_shelly():
    url = f"http://{shelly_ip}/relay/0?turn=toggle"
    try:
        global IsFirstShellyToggle
        response = requests.get(url)
        if response.status_code == 200 and IsFirstShellyToggle:
            IsFirstShellyToggle = False
            time.sleep(10)
            isPrinterConnected()
        elif not IsFirstShellyToggle:
            program()
        else:
            sendLogMessages("Fehler beim Umschalten des Shelly 1.")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{url}")
        time.sleep(100)
        program()



def isPrinterConnected():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        response = requests.get(api_endpoint, headers=headers)

        if response.status_code == 200:
            connection_data = response.json()
            if connection_data["current"]["state"] == "Operational" or connection_data["current"]["state"] == "Printing":
                waitOnJob()
            else:
                tryConnectPrinter()
        else:
            sendLogMessages(f"Fehler bei {api_endpoint}")
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def boolisPrinterConnected():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        response = requests.get(api_endpoint, headers=headers)

        if response.status_code == 200:
            connection_data = response.json()
            if connection_data["current"]["state"] == "Operational" or connection_data["current"]["state"] == "Printing":
                return True
            else:
                return False
        else:
            print("Fehler beim Herunterladen der Datei.")
            return False
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def tryConnectPrinter():
    api_endpoint = f"http://{octoprint_ip}/api/connection"
    try:
        data = {
            "port":"AUTO",
            "baudrate":0,
            "printerProfile":"_default",
            "autoconnect": True,
            "command":"connect"}
        header = {
            "X-Api-Key": "4E1BD42388C544499671AB3A5C83E5D6",
            "Content-Type": "application/json"
        }

        test = requests.post(api_endpoint, json=data, headers=header)
        if test.status_code == 204:
            isPrinterConnected()
        else:
            isPrinterConnected()
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def waitOnJob():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
        file_content = download_and_read_file()
        UserLoggedIn = IsUserLoggedIn(file_content)
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            job_info = response.json()
            if job_info.get("state") == "Printing":
                sendLogMessages("Der Drucker ist am Drucken")
                Fileavailable()
                waitOnPrint()
            elif job_info.get("state") == "Operational" and UserLoggedIn:
                time.sleep(10)
                waitOnJob()
        else:
            sendLogMessages(f"Fehler beim Auslesen vom Job,{api_endpoint}")
            waitOnJob()
            time.sleep(10)
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def waitOnPrint():
    api_endpoint = f"http://{octoprint_ip}/api/job"
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            job_info = response.json()
            actprintSize = job_info.get("progress", {}).get("completion")
            if actprintSize == 100:
                sendLogMessages("Der Druck ist fertig")
                sendFinishedPrint()
                TurnOffPrinter()
            elif actprintSize < 100:
                time.sleep(50)
                waitOnPrint()
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def TurnOffPrinter():
    api_endpoint = f"http://{octoprint_ip}/api/printer/tool"
    try:
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            job_info = response.json()
            temp = job_info.get("tool0", {}).get("actual")
            #nur testweise auf 60
            if temp <= 40:
                toggle_shelly()
                sendLogMessages("Drucker wird jz ausgeschaltet")
                #schalte Lüfter aus
                program()
            else:
                #schalte lüfter an
                if isNewFileavailable():
                    program()
                time.sleep(10)
                TurnOffPrinter()
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def Fileavailable():
    api_endpoint = f"http://{octoprint_ip}/api/files"
    try:
        global job_info
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            job_info = response.json()
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def isNewFileavailable():
    api_endpoint = f"http://{octoprint_ip}/api/files"
    try:
        global job_info
        response = requests.get(api_endpoint, headers=headers)
        if response.status_code == 200:
            new_job_info = response.json()

            if job_info is None:
                job_info = new_job_info
                return False

            # Sicherstellen, dass job_info ein Dictionary ist
            if isinstance(job_info, str):
                job_info = json.loads(job_info)

            # Extrahieren der Hashes der neuen Dateien
            new_files = new_job_info.get('files', [])
            new_hashes = {file['hash'] for file in new_files}

            # Extrahieren der Hashes der alten Dateien
            old_files = job_info.get('files', [])
            old_hashes = {file['hash'] for file in old_files}

            # Überprüfen, ob es neue Dateien gibt
            if not old_hashes.issuperset(new_hashes):
                job_info = new_job_info
                return True

        return False
    except Exception as e:
        sendLogMessages(f"Fehler: {e},{api_endpoint}")
        time.sleep(100)
        program()

def capture_screenshot(stream_url):
    response = requests.get(stream_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"Failed to capture image from stream. Status code: {response.status_code}")


def sendFinishedPrint():
    stream_url = f'http://{octoprint_ip}/webcam/?action=snapshot'
    try:
        sendLogMessages("Druck ist fertig!")
        TurnLightOnOffScreenshot(True)
        image = capture_screenshot(stream_url)
        time.sleep(10)
        TurnLightOnOffScreenshot(False)
        sendFinishPicture(image)
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")

def TurnLightOnOffScreenshot(Light):
    try:
        if Light:
            publish_message("true")
        elif not Light:
            publish_message("false")
    except Exception as e:
        sendLogMessages(f"Fehler: {e}")
        time.sleep(100)
        program()

program()

import requests

TOKEN = '7288374888:AAGn3-qDhWBiTShLjWWmwEhytYH_Sf4oXvI'
CHAT_ID = '6034992586'

def sendLogMessages(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    response = requests.post(url, data=payload)
    return response.json()

def sendFinishPicture(photo):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        'chat_id': CHAT_ID
    }
    files = {
        'photo': ('screenshot.jpg', photo, 'image/jpeg')
    }
    response = requests.post(url, data=payload, files=files)
    return response.json()

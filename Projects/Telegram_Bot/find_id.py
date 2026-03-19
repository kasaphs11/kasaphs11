from telethon.sync import TelegramClient

api_id = 29990481       # το δικό σου
api_hash = 'c8084f89e07ea776850faea8a14e07e9'

#api_id= 20504807
#api_hash='02b2e452b0467ec9b501fb8afad81e34'

with TelegramClient('my_session', api_id, api_hash) as client:
    dialogs = client.get_dialogs()
    for dialog in dialogs:
        print(f'{dialog.name} -> ID: {dialog.id}')

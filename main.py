import requests
from telethon import TelegramClient, events, sync
from telethon.tl.custom import Button

import os
from enum import Enum, auto

# TODO: Switch request to async lib

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('TOKEN')

client = TelegramClient('my acc', api_id, api_hash).start()
bot = TelegramClient('notes bot', api_id, api_hash).start(bot_token=bot_token)

make_note_btn = Button.text('Сделать заметку', resize=True)
my_notes_btn = Button.text('Мои записки', resize=True)
cancel_btn = Button.text('Отмена', resize=True)

start_kb = [make_note_btn, my_notes_btn]


class State(Enum):
    WAIT_USERNAME = auto()
    WAIT_NOTE_TEXT = auto()


conversation_state = {}
notes_view_state = {}
note_info_tmp_dict = {}


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await bot.send_message(
        event.chat,
        'Это бот для заметок пользователям телеграм.',
        buttons=start_kb
    )
    user = event.sender
    user_dict = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'phone': user.phone,
        'photo': user.photo.photo_id if user.photo else None
    }
    try:
        requests.post('http://127.0.0.1:8000/api/create-profile', json=user_dict)
    except:
        pass
    raise events.StopPropagation


@bot.on(events.CallbackQuery())
async def callback(event):
    sender = event.sender
    query = event.query
    state = notes_view_state[sender.id]
    if event.data == b'notes_forward':
        if len(state['notes']) - 1 == state['current_note']:
            state['current_note'] = 0
        else:
            state['current_note'] += 1
    elif event.data == b'notes_back':
        state['current_note'] -= 1

    crt_note_data = state["notes"][state["current_note"]]
    await bot.edit_message(
        event.chat_id,
        query.msg_id,
        f'**Записка №{crt_note_data["id"]}**\n'
        f'{crt_note_data["text"]}\n\n'
        f'Кому: @{crt_note_data["note_getter"]}',
        buttons=[Button.inline('⬅️ Назад', 'notes_back'), Button.inline('Вперед ➡️', 'notes_forward')]
    )
    raise events.StopPropagation


@bot.on(events.NewMessage(pattern='Мои записки'))
async def view_notes(event):
    sender = event.sender
    who = event.sender_id
    notes = requests.get(f'http://127.0.0.1:8000/api/notes/{sender.id}').json()

    if notes:
        notes_view_state[who] = {
            'notes': notes,
            'current_note': 0,
        }
        state = notes_view_state[sender.id]
        crt_note_data = state["notes"][state["current_note"]]
        await bot.send_message(
            event.chat_id,
            f'**Записка №{crt_note_data["id"]}**\n'
            f'{crt_note_data["text"]}\n\n'
            f'Кому: @{crt_note_data["note_getter"]}',
            buttons=[Button.inline('⬅️ Назад', 'notes_back'), Button.inline('Вперед ➡️', 'notes_forward')]
        )
    else:
        await bot.send_message(
            event.chat_id,
            'У вас пока нет записок.'
        )
    raise events.StopPropagation


@bot.on(events.NewMessage())
async def create_note_fsm(event):
    sender = event.sender
    who = event.sender_id
    msg = event.message
    state = conversation_state.get(who)

    if state is None:
        if event.text == 'Сделать заметку':
            await bot.send_message(
                event.chat_id,
                'Напишите никнейм/телефон человека, которому хотите написать заметку, или перешлите его сообщение.',
                buttons=cancel_btn
            )
        conversation_state[who] = State.WAIT_USERNAME

    elif state == State.WAIT_USERNAME:
        if msg.raw_text == "Отмена":
            del note_info_tmp_dict[who]
            del conversation_state[who]
            await start(event)
        user = await get_user_by_msg(msg)
        if user:
            await bot.send_message(
                event.chat_id,
                'Напишите текст записки.'
            )
            note_info_tmp_dict[who] = {'note_getter': user}
            conversation_state[who] = State.WAIT_NOTE_TEXT
        else:
            await bot.send_message(
                event.chat_id,
                'Пользователь не найден. Проверьте правильность введенных данных и попробуйте снова.',
                buttons=cancel_btn
            )

    elif state == State.WAIT_NOTE_TEXT:
        if msg.raw_text == 'Отмена':
            del note_info_tmp_dict[who]
            del conversation_state[who]
            await start(event)
        note_text = msg.raw_text
        note_getter = note_info_tmp_dict[who]['note_getter']
        data = {
            'note_creator': {
                'telegram_id': sender.id,
                'first_name': sender.first_name,
                'last_name': sender.last_name,
                'username': sender.username,
                'phone': sender.phone,
                'photo': sender.photo.photo_id if sender.photo else None
            },
            'note_getter': {
                'telegram_id': note_getter.id,
                'first_name': note_getter.first_name,
                'last_name': note_getter.last_name,
                'username': note_getter.username,
                'phone': note_getter.phone,
                'photo': note_getter.photo.photo_id if note_getter.photo else None
            },
            'text': note_text
        }
        try:
            requests.post('http://127.0.0.1:8000/api/create-note', json=data)
            await bot.send_message(
                event.chat_id,
                'Записка успешно добавлена.',
                buttons=start_kb
            )
        except:
            await bot.send_message(
                event.chat_id,
                'Что то пошло не так :(',
                buttons=start_kb
            )
        del note_info_tmp_dict[who]
        del conversation_state[who]

    raise events.StopPropagation


async def get_user_by_msg(msg):
    user = None
    fwd_msg = msg.fwd_from
    search_query = fwd_msg.from_id if fwd_msg else msg.raw_text
    try:
        user = await bot.get_entity(search_query)
    except ValueError:
        try:
            user = await client.get_entity(search_query)
        except ValueError:
            pass
    return user


if __name__ == '__main__':
    print('Бот запущен')
    bot.run_until_disconnected()

import requests
from telethon import TelegramClient, events, sync
from telethon.tl.custom import Button
from dateutil import parser

import os
import json

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
		'photos': [{
			'photo_id': user.photo.photo_id
		}] if user.photo else None
	}
	try:
		r = requests.post('http://127.0.0.1:8000/api/create-profile', json=user_dict)
	except:
		pass
	raise events.StopPropagation


async def cb_filter(event):
	data = json.loads(event.data)
	if not data:
		return False
	if 'view_notes_friend' in data.keys():
		return True
	return False


@bot.on(events.CallbackQuery(func=cb_filter))
async def callback(event):
	data = json.loads(event.data)
	friend_tg_id = data.get('view_notes_friend').get('tg_id')
	r = requests.get(f'http://127.0.0.1:8000/api/notes/{event.sender.id}/', params={'sent_to': friend_tg_id})
	if r.status_code == 200:
		notes = r.json()
	else:
		await event.respond('Какая то ошибка на сервере :(')
		raise events.StopPropagation
	note_str_list = []
	for note in notes:
		time_str = parser.parse(note.get('created')).strftime('%d.%m.%y %H:%M%S')
		note_str = f'```{time_str}```\n{note.get("text")}'
		note_str_list.append(note_str)
	msg = '\n----------------------\n'.join(note_str_list)
	await event.respond(
		msg,
		buttons=start_kb
	)
	raise events.StopPropagation


@bot.on(events.CallbackQuery())
async def callback(event):
	sender = event.sender
	state = notes_view_state.get(sender.id)
	if not state:
		raise events.StopPropagation

	if event.data == b'notes_forward':
		if len(state['notes']) - 1 == state['current_note']:
			state['current_note'] = 0
		else:
			state['current_note'] += 1
	elif event.data == b'notes_back':
		state['current_note'] -= 1

	crt_note_data = state["notes"][state["current_note"]]
	await event.edit(
		f'{crt_note_data["text"]}\n\n'
		f'Кому: @{crt_note_data["note_getter"]["username"]}',
		buttons=[Button.inline('⬅️ Назад', 'notes_back'), Button.inline('Вперед ➡️', 'notes_forward')]
	)
	raise events.StopPropagation


@bot.on(events.NewMessage(pattern='Мои записки'))
async def view_notes(event):
	r = requests.get(f'http://127.0.0.1:8000/api/friends/{event.sender.id}/')
	if r.status_code == 200:
		friends = r.json()
	else:
		await event.respond('Какая то ошибка на сервере :(')
		raise events.StopPropagation

	if not friends:
		await event.respond('У вас пока нет записок.')
		raise events.StopPropagation

	buttons = []
	for i in friends:
		cb_data = json.dumps({
			'view_notes_friend': {'tg_id': i.get('telegram_id')}
		})
		buttons.append([Button.inline(f'{i.get("username")}', cb_data)])
	await event.respond(
		'Выберите пользователя, которому была оставлена заметка.',
		buttons=buttons
	)


@bot.on(events.NewMessage())
async def create_note_fsm(event):
	sender = event.sender
	who = event.sender_id
	msg = event.message
	state = conversation_state.get(who)

	if msg.raw_text == "Отмена":
		try:
			del note_info_tmp_dict[who]
			del conversation_state[who]
		except KeyError:
			pass
		await start(event)

	if state is None:
		if event.text == 'Сделать заметку':
			await bot.send_message(
				event.chat_id,
				'Напишите никнейм/телефон человека, которому хотите написать заметку, или перешлите его сообщение.',
				buttons=cancel_btn
			)
			conversation_state[who] = State.WAIT_USERNAME

	elif state == State.WAIT_USERNAME:
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
		note_text = msg.raw_text
		note_getter = note_info_tmp_dict[who]['note_getter']
		data = {
			'creator': {
				'telegram_id': sender.id,
				'first_name': sender.first_name,
				'last_name': sender.last_name,
				'username': sender.username,
				'phone': sender.phone,
				'photos': [{'photo_id': sender.photo.photo_id}] if sender.photo else None
			},
			'note_getter': {
				'telegram_id': note_getter.id,
				'first_name': note_getter.first_name,
				'last_name': note_getter.last_name,
				'username': note_getter.username,
				'phone': note_getter.phone,
				'photos': [{'photo_id': note_getter.photo.photo_id}] if note_getter.photo else None
			},
			'text': note_text
		}
		try:
			r = requests.post('http://127.0.0.1:8000/api/create-note', json=data)
			if r.status_code == 200:
				await bot.send_message(
					event.chat_id,
					'Записка успешно добавлена.',
					buttons=start_kb
				)
			else:
				await bot.send_message(
					event.chat_id,
					'Какая то ошибка на сервере :(',
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

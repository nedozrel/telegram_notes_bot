from telethon import TelegramClient, events, sync
from telethon.tl.custom import Button

import os
from enum import Enum, auto

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('TOKEN')

client = TelegramClient('my acc', api_id, api_hash).start()
bot = TelegramClient('notes bot', api_id, api_hash).start(bot_token=bot_token)

make_note_btn = Button.text('Сделать заметку', resize=True)
cancel_btn = Button.text('Отмена', resize=True)


class State(Enum):
	WAIT_USERNAME = auto()
	WAIT_NOTE_TEXT = auto()


conversation_state = {}
note_info_tmp_dict = {}


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
	await bot.send_message(
		event.chat,
		'Это бот для заметок пользователям телеграм.',
		buttons=make_note_btn
	)
	# TODO: Saving user to the db
	raise events.StopPropagation


@bot.on(events.NewMessage())
async def create_note_fsm(event):
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
		note_text = msg.raw_text
		note_info_tmp_dict[who]['note_text'] = note_text
		await create_note_on_server(who)
		await event.respond('Записка успешно добавлена.')
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


async def create_note_on_server(sender):
	# TODO: create note API call
	pass


if __name__ == '__main__':
	print('Бот запущен')
	bot.run_until_disconnected()

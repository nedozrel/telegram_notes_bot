from telethon import TelegramClient, events, sync
from telethon.tl.custom import Button

import os

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('TOKEN')

client = TelegramClient('my acc', api_id, api_hash).start()
bot = TelegramClient('notes bot', api_id, api_hash).start(bot_token=bot_token)

make_note_btn = Button.text('Сделать заметку', resize=True)
cansel_btn = Button.text('Отмена', resize=True)


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
	await bot.send_message(
		event.chat,
		'Это бот для заметок пользователям телеграм.',
		buttons=make_note_btn
	)
	# TODO: Saving user to the db
	raise events.StopPropagation


@bot.on(events.NewMessage(pattern='Сделать заметку'))
async def create_note_conv(event):
	async with bot.conversation(event.chat) as conv:
		await conv.send_message(
			'Напишите никнейм/телефон человека, которому хотите написать заметку, или перешлите его сообщение.',
			buttons=Button.clear()
		)
		resp = await conv.get_response()
		user = await get_user_by_msg(resp)
		while not user:
			await conv.send_message(
				'Пользователь не найден. Проверьте правильность введенных данных и попробуйте снова.')
			resp = await conv.get_response()
			user = await get_user_by_msg(resp)
		await conv.send_message(
			f'Пользователь {user.username} найден\nID - {user.id}',
			buttons=make_note_btn
		)
		# TODO: Actions after getting a user
		print(user)

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

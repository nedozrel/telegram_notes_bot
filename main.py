from telethon import TelegramClient, events, sync

import os

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('TOKEN')

client = TelegramClient('my acc', api_id, api_hash).start()
bot = TelegramClient('notes bot', api_id, api_hash).start(bot_token=bot_token)


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
	await event.respond('Это бот для заметок пользователям телеграм.')
	raise events.StopPropagation


@bot.on(events.NewMessage())
async def echo(event):
	user = ''
	try:
		user = await bot.get_entity(event.text)
	except ValueError:
		try:
			user = await client.get_entity(event.text)
		except ValueError:
			await event.respond('Пользователь не найден')
	if user:
		await event.respond(f'User id - {user.id}')


if __name__ == '__main__':
	print('Бот запущен')
	bot.run_until_disconnected()

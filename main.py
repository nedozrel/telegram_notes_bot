from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import os


class FSMUser(StatesGroup):
	note = State()
	submit_note = State()


API_TOKEN = os.getenv('TOKEN')

submit_button = KeyboardButton('Подтвердить')
decline_button = KeyboardButton('Отмена')
submit_kb = ReplyKeyboardMarkup(resize_keyboard=True).row(submit_button, decline_button)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
	print(message)
	text = "Перешлите сообщение чтобы оставить заметку пользователю"
	await message.answer(text)


@dp.message_handler()
async def main(message: types.Message):
	if message.is_forward():
		print(message)
		await FSMUser.note.set()
		await message.answer('Напишите заметку по данному пользователю')


@dp.message_handler(content_types=['text'], state=FSMUser.note)
async def save_note(message: types.Message, state: FSMContext):
	await FSMUser.next()
	async with state.proxy() as data:
		data['note'] = message.text
	await message.answer(
		f'Добавить заметку? \n'
		f'"{message.text}"',
		reply_markup=submit_kb
	)


@dp.message_handler(content_types=['text'], state=FSMUser.submit_note)
async def submit_note(message: types.Message, state: FSMContext):
	if message.text.lower() in ("подтвердить", 'да'):
		async with state.proxy() as data:
			note_text = data['note']

		await message.answer(f'Заметка "{note_text}" успешно добавлена', reply_markup=ReplyKeyboardRemove())
	elif message.text.lower() in ("отмена", "нет"):
		await message.answer('Заметка отменена', reply_markup=ReplyKeyboardRemove())
	else:
		await message.answer('Я вас не понял', reply_markup=ReplyKeyboardRemove())
	await state.finish()

if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)

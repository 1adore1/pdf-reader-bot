import io
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import API_TOKEN
from PyPDF2 import PdfReader

# API_TOKEN = '7168496497:AAENOQkMy0mYSVdPBRzvk_WzJaggxyOc-jY'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
users_books = {}

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

users_books = load_data('users_books.json')

def extract_text_from_pdf(pdf_file):
    pdf = PdfReader(pdf_file)
    text = ''
    for page_num in range(len(pdf.pages)):
        text += pdf.pages[page_num].extract_text()
    return text


def split_text_into_pages(text):
    words = text.split(' ')
    pages = [' '.join(words[i:i + 100]) for i in range(0, len(words), 100)]
    return pages


def get_navigation_keyboard(page_index, total_pages):
    builder = InlineKeyboardBuilder()
    if page_index > 0:
        builder.add(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'prev_{page_index}'))
    if page_index < total_pages - 1:
        builder.add(InlineKeyboardButton(text='Вперед ➡️', callback_data=f'next_{page_index}'))
    builder.add(InlineKeyboardButton(text=f"{page_index + 1}/{total_pages}", callback_data="page_info", disabled=True))
    return builder.as_markup()

def get_library_keyboard(chat_id):
    builder = InlineKeyboardBuilder()
    i = 0
    for book in users_books[chat_id]:
        builder.add(InlineKeyboardButton(text=book, callback_data=f'book_{i}'))
        i += 1
    return builder.as_markup()


@dp.message(Command('start'))
async def start_command(message: types.Message):
    chat_id = message.chat.id
    if chat_id in users_books:
        await message.answer('Список загруженных книг: ', reply_markup=get_library_keyboard())
    else:
        await message.answer('Привет! Здесь ты можешь удобно читать книги.')


@dp.message(F.document.mime_type == 'application/pdf')
async def handle_new_pdf(message: types.Message):
    chat_id = message.chat.id
    if chat_id in users_books:
        if message.document.file_name in users_books[chat_id]:
            await message.answer('Книга уже скачана.')
            await message.answer('Список загруженных книг: ', reply_markup=get_library_keyboard())
    else:
        pdf_file = io.BytesIO()
        await bot.download(file=message.document, destination=pdf_file)
        await message.answer('Идёт загрузка файла...')
        try:
            text = extract_text_from_pdf(pdf_file)
            pages = split_text_into_pages(text)
            users_books[chat_id] = pages
            await message.answer(pages[0], reply_markup=get_navigation_keyboard(0, len(pages)))
            save_data(users_books, 'users_books.json') 
        except Exception as e:
            await message.reply('Произошла ошибка при обработке PDF файла.')
            logging.error(f'Error processing PDF: {e}')


@dp.callback_query(F.data.startswith(('prev_', 'next_')))
async def process_navigation(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    
    data = callback_query.data.split('_')
    action, page_index = data[0], int(data[1])
    
    if action == 'prev':
        new_index = page_index - 1
    elif action == 'next':
        new_index = page_index + 1
    else:
        return
    
    pages = users_books[chat_id]
    text = pages[new_index]
    await bot.edit_message_text(text, chat_id=chat_id, message_id=callback_query.message.message_id,
                                reply_markup=get_navigation_keyboard(new_index, len(pages)))
    await callback_query.answer()


@dp.message()
async def handle_page_number(message: types.Message):
    chat_id = message.chat.id
    try:
        page_number = int(message.text)
        if chat_id in users_books:
            pages = users_books[chat_id]
            total_pages = len(pages)
            if 1 <= page_number <= total_pages:
                await bot.delete_message(chat_id=chat_id, message_id=message.message_id - 1)
                await message.answer(pages[page_number - 1], reply_markup=get_navigation_keyboard(page_number - 1, total_pages))
            else:
                await message.answer(f"Пожалуйста, введите номер страницы от 1 до {total_pages}.")
        else:
            await message.answer("Пожалуйста, отправьте PDF файл.")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер страницы.")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
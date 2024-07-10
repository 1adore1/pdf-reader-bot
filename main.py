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


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
users_books = {}
books = {}

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
users_books = {int(k): v for k, v in users_books.items()}
books = load_data('books.json')

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


def get_navigation_keyboard(page_index, total_pages, filename):
    builder = InlineKeyboardBuilder()
    if page_index > 0:
        builder.add(InlineKeyboardButton(text='⬅️', callback_data=f'prev_{filename}_{page_index}'))
    if page_index < total_pages - 1:
        builder.add(InlineKeyboardButton(text='➡️', callback_data=f'next_{filename}_{page_index}'))
    builder.add(InlineKeyboardButton(text=f'{page_index + 1}/{total_pages}', callback_data='page_info', disabled=True))
    builder.add(InlineKeyboardButton(text='Файлы', callback_data='downloads'))
    return builder.as_markup()


def get_library_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    i = 0
    for book in users_books[user_id]:
        builder.add(InlineKeyboardButton(text=book.split('.')[0], callback_data=f'book_{book}')) 
        i += 1
    return builder.as_markup()


def get_start_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    # builder.add(InlineKeyboardButton(text='Загрузить файл', callback_data='load_file'))
    try:
        if users_books[user_id] is not None:
            builder.add(InlineKeyboardButton(text='Загруженные файлы', callback_data='downloads'))
    except:
        pass
    return builder.as_markup()


@dp.message(Command('start'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Привет! Здесь ты можешь удобно читать книги.', reply_markup=get_start_keyboard(user_id))


@dp.message(Command('downloads'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Загруженные файлы:', reply_markup=get_library_keyboard(user_id))


@dp.message(F.document.mime_type == 'application/pdf')
async def handle_new_pdf(message: types.Message):
    user_id = message.chat.id
    filename = message.document.file_name

    if user_id in users_books and filename in users_books[user_id]:
        await message.answer('Книга уже скачана. Список загруженных книг: ', reply_markup=get_library_keyboard(user_id))
    else:
        pdf_file = io.BytesIO()
        await bot.download(file=message.document, destination=pdf_file)
        await message.answer('Идёт загрузка файла...')

        text = extract_text_from_pdf(pdf_file)
        pages = split_text_into_pages(text)
        if user_id not in users_books:
            users_books[user_id] = []
        users_books[user_id].append(filename)
        books[filename] = pages

        await message.answer(pages[0], reply_markup=get_navigation_keyboard(0, len(pages), filename))
        save_data(users_books, 'users_books.json') 
        save_data(books, 'books.json')


@dp.callback_query(F.data == 'downloads')
async def downloads(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Загруженные файлы:', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_library_keyboard(user_id))


@dp.callback_query(F.data.startswith('book_'))
async def downloads(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('_')
    filename = data[1]
    pages = books[filename]
    await bot.edit_message_text(pages[0], chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_navigation_keyboard(0, len(pages), filename))


# turn page
@dp.callback_query(F.data.startswith(('prev_', 'next_')))
async def process_navigation(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id

    data = callback_query.data.split('_')
    action, filename, page_index = data[0], data[1], int(data[2])
    
    if action == 'prev':
        new_index = page_index - 1
    elif action == 'next':
        new_index = page_index + 1
    else:
        return
    
    pages = books[filename]
    text = pages[new_index]
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_navigation_keyboard(new_index, len(pages), filename))
    # await callback_query.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
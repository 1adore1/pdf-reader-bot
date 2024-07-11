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

# func for extracting text from pdf
def extract_text_from_pdf(pdf_file):
    pdf = PdfReader(pdf_file)
    text = ''
    for page_num in range(len(pdf.pages)):
        text += pdf.pages[page_num].extract_text()
    return text


# func for split text on pages
def split_text_into_pages(text):
    words = text.split(' ')
    pages = [' '.join(words[i:i + 100]) for i in range(0, len(words), 100)]
    return pages


# func for save data in .json
def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# func for load data from .json
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


# dispatcher for command /start
@dp.message(Command('start'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Here you can read files with all comfort of telegram gui.', reply_markup=get_start_keyboard(user_id))


# displatcher for command /downloads
@dp.message(Command('downloads'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Downloads:', reply_markup=get_downloads_keyboard(user_id))


# keyboard for command /start
def get_start_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Load file', callback_data='load__file'))
    try:
        if users_books[user_id] is not None:
            builder.add(InlineKeyboardButton(text='Downloads', callback_data='downloads'))
    except:
        pass
    return builder.as_markup()


# keyboard for command /downloads
def get_downloads_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Back to start', callback_data='back__start'))
    for book in users_books[user_id]:
        builder.add(InlineKeyboardButton(text=book.split('.')[0], callback_data=f'book__{book}')) 
    return builder.as_markup()


# keyboard for turning page
def get_nav_keyboard(page_index, total_pages, filename):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='⬅️', callback_data=f'prev__{filename}__{page_index}'))
    builder.add(InlineKeyboardButton(text=f'{page_index + 1}/{total_pages}', callback_data='page__info', disabled=True))
    builder.add(InlineKeyboardButton(text='➡️', callback_data=f'next__{filename}__{page_index}'))
    builder.add(InlineKeyboardButton(text='Back to files', callback_data='downloads'))
    builder.add(InlineKeyboardButton(text='Delete file', callback_data=f'delete__{filename}__{page_index}'))
    builder.adjust(3, 2)
    return builder.as_markup()


# keyboard for confirm deleting
def get_confirm_delete_keyboard(filename, page_index):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Yes', callback_data=f'confirm__delete__{filename}'))
    builder.add(InlineKeyboardButton(text='Cancel', callback_data=f'cancel__delete__{filename}__{page_index}'))
    return builder.as_markup()


# keyboard for loading file
def get_load_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Back to start', callback_data='back__start'))
    return builder.as_markup()


# dispatcher for sending file
@dp.message(F.document.mime_type == 'application/pdf')
async def handle_new_pdf(message: types.Message):
    user_id = message.chat.id
    filename = message.document.file_name

    if user_id in users_books and filename in users_books[user_id]:
        # await bot.delete_message(chat_id=user_id, message_id=message.message_id - 1)
        await message.answer('File already loaded. Downloads: ', reply_markup=get_downloads_keyboard(user_id))
    else:
        pdf_file = io.BytesIO()
        await bot.download(file=message.document, destination=pdf_file)
        await message.answer('File is loading...')

        text = extract_text_from_pdf(pdf_file)
        pages = split_text_into_pages(text)
        if user_id not in users_books:
            users_books[user_id] = []
        users_books[user_id].append(filename)
        books[filename] = pages
        # await bot.delete_message(chat_id=user_id, message_id=message.message_id - 1)
        await bot.edit_message_text(filename, chat_id=user_id, message_id=message.message_id + 1)
        await message.answer(pages[0], reply_markup=get_nav_keyboard(0, len(pages), filename))
        save_data(users_books, 'users_books.json') 
        save_data(books, 'books.json')


# dispatcher for button "load file"
@dp.callback_query(F.data == 'load__file')
async def load_file(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Send file for load.', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_load_keyboard())


# dispatcher for button "back__start"
@dp.callback_query(F.data == 'back__start')
async def back_start(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Here you can read files with all comfort of telegram gui.', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_start_keyboard(user_id))



# dispatcher for button "downloads"
@dp.callback_query(F.data == 'downloads')
async def downloads(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Downloads:', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_downloads_keyboard(user_id))


# dispatcher for button "select book"
@dp.callback_query(F.data.startswith('book__'))
async def select_book(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename = data[1]
    pages = books[filename]
    await bot.edit_message_text(pages[0], chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(0, len(pages), filename))


# dispatcher for button "turn page"
@dp.callback_query(F.data.startswith(('prev__', 'next__')))
async def nav_file(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id

    data = callback_query.data.split('__')
    action, filename, page_index = data[0], data[1], int(data[2])
    pages = books[filename]

    if action == 'prev':
        if page_index - 1 < 0:
            return
        else:
            new_index = page_index - 1
    elif action == 'next':
        if page_index + 1 > len(pages):
            return
        else:
            new_index = page_index + 1
    
    text = pages[new_index]
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(new_index, len(pages), filename))


# dispatcher for button "delete book"
@dp.callback_query(F.data.startswith('delete__'))
async def delete_book(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[1], int(data[2])
    await bot.edit_message_text(f'You are about to delete "{filename}". Is that correct?', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_confirm_delete_keyboard(filename, page_index))


# dispatcher for button "confirm__delete"
@dp.callback_query(F.data.startswith('confirm__delete__'))
async def confirm_delete(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename = data[2]
    ind = users_books[user_id].index(filename)
    del users_books[user_id][ind]
    del books[filename]
    await bot.edit_message_text('Downloads:', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_downloads_keyboard(user_id))


# dispatcher for button "cancel__delete"
@dp.callback_query(F.data.startswith('cancel__delete__'))
async def cancel_delete(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[2], int(data[3])
    pages = books[filename]
    text = pages[page_index]
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(page_index, len(pages), filename)) 


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
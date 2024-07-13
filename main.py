import io
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import API_TOKEN
from PyPDF2 import PdfReader


class UserAnswer(StatesGroup):
    file = State()
    page = State()
    filename = State()
    page_index = State()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
users_files = {}
files_pages = {}

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


users_files = load_data('users_files.json')
users_files = {int(k): v for k, v in users_files.items()}
files_pages = load_data('files_pages.json')



# MESSAGE FOR COMMAND /start
@router.message(Command('start'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Here you can read files with all comfort of telegram gui.', reply_markup=get_start_keyboard(user_id))

# KEYBOARD FOR START
def get_start_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Load file', callback_data='load_file'))
    try:
        if users_files[user_id] is not None:
            builder.add(InlineKeyboardButton(text='Downloads', callback_data='downloads'))
    except:
        pass
    return builder.as_markup()



# HANDLING COMMAND /downloads
@router.message(Command('downloads'))
async def start_command(message: types.Message):
    user_id = message.chat.id
    await message.answer('Downloads:', reply_markup=get_downloads_keyboard(user_id))

# MESSAGE FOR DOWNLOADS
@router.callback_query(F.data == 'downloads')
async def downloads(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Downloads:', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_downloads_keyboard(user_id))

# KEYBOARD FOR DOWNLOADS
def get_downloads_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Back to start', callback_data='back_start'))
    for file in users_files[user_id]:
        builder.add(InlineKeyboardButton(text=file[:21], callback_data=f'file__{file}')) 
    return builder.as_markup()



# WAITING FOR FILE
@router.callback_query(F.data == 'load_file')
async def load_file(callback_query: types.CallbackQuery, state=FSMContext):
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Send file for load.', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_load_keyboard())
    await state.set_state(UserAnswer.file)

# KEYBOARD FOR FILE LOADING
def get_load_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Back to start', callback_data='back_start'))
    return builder.as_markup()

# HANDLING FILE LOAD CANCELATION BUTTON 
@router.callback_query(F.data == 'back_start')
async def back_start(callback_query: types.CallbackQuery, state=FSMContext):
    await state.clear()
    user_id = callback_query.message.chat.id
    await bot.edit_message_text('Here you can read files with all comfort of telegram gui.', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_start_keyboard(user_id))

# HANDLING OF FILE LOADING
@router.message(UserAnswer.file) 
async def handle_new_pdf(message: types.Message, state: FSMContext):
    if message.document:
        await state.update_data(file=message.document)
        user_id = message.chat.id
        filename = message.document.file_name
        await state.clear()
        if user_id in users_files and filename in users_files[user_id]:
            await message.answer('File already loaded. Downloads: ', reply_markup=get_downloads_keyboard(user_id))
        else:
            pdf_file = io.BytesIO()
            await bot.download(file=message.document, destination=pdf_file)
            await message.answer('File is loading...')

            text = extract_text_from_pdf(pdf_file)
            pages = split_text_into_pages(text)
            if user_id not in users_files:
                users_files[user_id] = []
            users_files[user_id].append(filename)
            files_pages[filename] = pages

            await bot.edit_message_text(filename, chat_id=user_id, message_id=message.message_id + 1)
            await message.answer(pages[0], reply_markup=get_nav_keyboard(0, len(pages), filename))
            save_data(users_files, 'users_files.json') 
            save_data(files_pages, 'files_pages.json')
    else:
        await message.answer('Incorrect file type. Try again.')



# HANDLING FILE SELECTION BUTTONS
@router.callback_query(F.data.startswith('file__'))
async def select_file(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename = data[1]
    pages = files_pages[filename]
    await bot.edit_message_text(pages[0], chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(0, len(pages), filename))

# KEYBOARD FOR FILE NAVIGATION
def get_nav_keyboard(page_index, total_pages, filename):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='⬅️', callback_data=f'prev__{filename}__{page_index}'))
    builder.add(InlineKeyboardButton(text=f'{page_index + 1}/{total_pages}', callback_data=f'to_page__{filename}__{page_index}'))
    builder.add(InlineKeyboardButton(text='➡️', callback_data=f'next__{filename}__{page_index}'))
    builder.add(InlineKeyboardButton(text='Back to files', callback_data='downloads'))
    builder.add(InlineKeyboardButton(text='Delete file', callback_data=f'del__{filename}__{page_index}'))
    builder.adjust(3, 2)
    return builder.as_markup()



# HANDLING TURNING PAGES BUTTONS
@router.callback_query(F.data.startswith(('prev__', 'next__')))
async def nav_file(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    action, filename, page_index = data[0], data[1], int(data[2])
    pages = files_pages[filename]
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



# WAITING FOR CHOOSING PAGE
@router.callback_query(F.data.startswith('to_page__'))
async def to_page(callback_query: types.CallbackQuery, state=FSMContext):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[1], int(data[2])
    await state.set_state(UserAnswer.filename)
    await state.update_data(filename=filename)
    await state.set_state(UserAnswer.page_index)
    await state.update_data(page_index=page_index)
    pages = files_pages[filename]
    text = f'Selecting page for "{filename}".\nSend the number in range from 1 to {len(pages)}.'
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id, 
                                reply_markup=get_cancel_page_keyboard(filename, page_index))
    await state.set_state(UserAnswer.page)

# HANDLING OF ENTERING PAGE NUMBER
@router.message(UserAnswer.page)
async def send_page(message: types.Message, state=FSMContext):
    try:
        page_index = int(message.text) - 1
        await state.update_data(page=UserAnswer.page)
        user_data = await state.get_data()
        filename = user_data['filename']
        pages = files_pages[filename]
        if 0 <= page_index < len(pages):
            await message.answer(pages[page_index], reply_markup=get_nav_keyboard(page_index, len(pages), filename))
            await state.set_state(state=None)
        else:
            await message.answer('Incorrect page number. Try again.')
    except:
        await message.answer('Incorrect page number. Try again.')

# KEYBOARD FOR CHOOSING PAGE CANCELATION
def get_cancel_page_keyboard(filename, page_index):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Cancel', callback_data=f'cancel_page__{filename}__{page_index}'))
    return builder.as_markup()

# HANDLING CHOOSING CANCELATION BUTTON
@router.callback_query(F.data.startswith('cancel_page'))
async def cancel_page(callback_query: types.CallbackQuery, state=FSMContext):
    state.set_state(state=None)
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[1], int(data[2])
    pages = files_pages[filename]

    await bot.edit_message_text(pages[page_index], chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(page_index, len(pages), filename))



# HANDLING DELETE BUTTON
@router.callback_query(F.data.startswith('del__'))
async def del_file(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[1], int(data[2])
    text = f'You are about to delete "{filename}". Is that correct?'
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_confirm_del_keyboard(filename, page_index))

# KEYBOARD FOR DELETE CONFIRMATION
def get_confirm_del_keyboard(filename, page_index):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Yes', callback_data=f'confirm__del__{filename}'))
    builder.add(InlineKeyboardButton(text='Cancel', callback_data=f'cancel__del__{filename}__{page_index}'))
    return builder.as_markup()

# HANDLING DELETE CONFIRMATION BUTTON
@router.callback_query(F.data.startswith('confirm__del__'))
async def confirm_del(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename = data[2]
    ind = users_files[user_id].index(filename)
    del users_files[user_id][ind]
    del files_pages[filename]
    await bot.edit_message_text('Downloads:', chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_downloads_keyboard(user_id))

# HANDLING DELETE CANCELATION BUTTON
@router.callback_query(F.data.startswith('cancel__del__'))
async def cancel_del(callback_query: types.CallbackQuery):
    user_id = callback_query.message.chat.id
    data = callback_query.data.split('__')
    filename, page_index = data[2], int(data[3])
    pages = files_pages[filename]
    text = pages[page_index]
    await bot.edit_message_text(text, chat_id=user_id, message_id=callback_query.message.message_id,
                                reply_markup=get_nav_keyboard(page_index, len(pages), filename)) 



async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
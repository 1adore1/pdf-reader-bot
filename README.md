# PDF Reader Telegram Bot
https://github.com/user-attachments/assets/89eea885-362b-4d96-b81f-7e913538ea6b
### Overview

This bot allows users to upload and read PDF files directly within Telegram's chat interface. 
Users can upload a PDF, navigate between pages, and manage their files using an intuitive GUI. 
All files and their content are saved locally for easy retrieval and navigation.

### Installation
1. Clone the repository:
```
git clone https://github.com/1adore1/librarybot.git
cd librarybot
```
2. Install required libraries:
```
pip install aiogram PyPDF2
```
3. Run the bot:
```
python main.py
```
### Usage
* **Upload a File:** Click on "Load file", then send a PDF document. The bot will process the file and split the text into "pages".
* **Navigate Pages**: Use the "⬅️" and "➡️" buttons to go back and forth between pages of the PDF.
* **Delete a File**: Select a file and use the "Delete" button to remove it from storage.

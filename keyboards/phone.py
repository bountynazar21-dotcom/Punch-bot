# keyboards/phone.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавіатура для запиту номера телефону
request_phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

#!/usr/bin/python3

import time, configparser

import telebot
from telebot import types

from influxdb import InfluxDBClient

config = configparser.ConfigParser()
config.read_file(open('./token.config', mode='r'))
token = config.get('config', 'token')
host = config.get('config', 'host')
user = config.get('config', 'user')
password = config.get('config', 'password')
dbname = config.get('config', 'dbname')

commands = {
    'start': 'Begrüßung & Scan',
    'hilfe': 'Informationen zur Bedienung',
    'erinnern': 'Die Erinnerung starten',
    'aktuell': 'Auswertung der Selbstfürsorge'
}

number_board = types.ReplyKeyboardMarkup(one_time_keyboard=True)
itembtna = types.KeyboardButton('1')
itembtnv = types.KeyboardButton('2')
itembtnc = types.KeyboardButton('3')
itembtnd = types.KeyboardButton('4')
itembtne = types.KeyboardButton('5')
itembtnf = types.KeyboardButton('6')
number_board.row(itembtna, itembtnv, itembtnc)
number_board.row(itembtnd, itembtne, itembtnf)

hideBoard = types.ReplyKeyboardRemove()


def listener(messages):
    for m in messages:
        if m.content_type == 'text':
            print(str(m.chat.first_name) + " [" + str(m.chat.id) + "]: " + m.text)


def beep(cid):
    bot.send_message(cid, "Vergib eine Note für deine Selbstfürsorge:", reply_markup=number_board)
    data.store_userStep(cid, 2)


bot = telebot.TeleBot(token)
bot.set_update_listener(listener)


# Start
@bot.message_handler(commands=['start'])
def command_start(m):
    cid = m.chat.id
    first_name = m.from_user.first_name
    last_name = m.from_user.last_name
    username = m.from_user.username
    db_cid = data.get_user(cid)
    if cid != db_cid:
        userStep = 0
        user_data = [
            (cid, first_name, last_name, username, userStep)
        ]
        data.store_user(user_data)
        bot.send_message(cid, "Hallo " + first_name + ", lass mich dich scannen...")
        time.sleep(2)
        bot.send_message(cid, "Scan abgeschlossen.")
        command_help(m)
    else:
        bot.send_message(cid, "Du bist im System unter der Numer " + str(cid) + " bereits registriert.")


# Hilfe
@bot.message_handler(commands=['hilfe'])
def command_help(m):
    cid = m.chat.id
    help_text = "Die folgenden Optionen sind verfügbar: \n"
    for key in commands:
        help_text += "/" + key + ": "
        help_text += commands[key] + "\n"
    bot.send_message(cid, help_text)


# Auswertung
@bot.message_handler(commands=['aktuell'])
def auswertung(m):
    cid = m.chat.id
    data = client.query('SELECT * FROM wetterstation GROUP BY * ORDER BY DESC LIMIT 1')
    bot.send_message(cid, data)


# Erinnern lassen
@bot.message_handler(commands=['erinnern'])
def erinnern(m):
    cid = m.chat.id
    bot.send_message(cid, "In wie vielen Minuten soll ich dich erinnern?")
    data.store_userStep(cid, 1)


# Erinnerung einstellen
@bot.message_handler(func=lambda message: data.get_userstep(message.chat.id) == 1)
def set_timer(m):
    cid = m.chat.id
    text = m.text
    args = text.split()

    bot.send_chat_action(cid, 'typing')

    if len(args) == 1 and args[0].isdigit():
        sec = int(args[0])
        schedule.every(sec).minutes.do(beep, cid).tag(cid)
        bot.send_message(cid, "Erinnerung gestellt!")
        data.store_userStep(cid, 0)
    else:
        bot.reply_to(m, 'Bitte nur die Anzahl der Minuten eingeben.')
        bot.send_message(m, 'Bitte erneut versuchen.')


# Selbstfürsorge Nummer
@bot.message_handler(func=lambda message: data.get_userstep(message.chat.id) == 2)
def sfn(m):
    cid = m.chat.id
    nummer = m.text
    if nummer.isdigit():
        bot.send_chat_action(cid, 'typing')
        bot.send_message(cid, "Wie geht es die gerade?", reply_markup=hideBoard)
        data.store_userStep(cid, 3)
    else:
        bot.send_message(cid, "Bitte vorgegebenes Keyboard benutzen!")
        beep(cid)


# Selbstfürsorge Text
@bot.message_handler(func=lambda message: data.get_userstep(message.chat.id) == 3)
def sft(m):
    cid = m.chat.id
    text = m.text
    bot.send_chat_action(cid, 'typing')
    bot.send_message(cid, "Danke! Pass weiterhin auf dich auf!", reply_markup=hideBoard)
    data.store_userStep(cid, 0)


# Stop
@bot.message_handler(commands=['stop'])
def unset_timer(message):
    schedule.clear(message.chat.id)
    bot.reply_to(message, "Erinnerung deaktiviert!")


# Easteregg
@bot.message_handler(func=lambda message: message.text == "Easteregg")
def easteregg(m):
    bot.send_message(m.chat.id, "I love you!")


# Standard Handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    bot.send_message(m.chat.id, "Ich verstehe \"" + m.text + "\"nicht. Bitte /hilfe eingeben.")


if __name__ == '__main__':
    threading.Thread(target=bot.infinity_polling, name='bot_infinity_polling', daemon=True).start()
    client = InfluxDBClient(host, 8086, user, password, dbname)
    while True:
        schedule.run_pending()
        time.sleep(1)
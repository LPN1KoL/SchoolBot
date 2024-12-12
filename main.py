from datetime import datetime, timedelta
from pprint import pprint
from pydnevnikruapi.dnevnik import dnevnik
import pymysql
import telebot
import threading
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from platform import system
from pyvirtualdisplay import Display
from selenium.webdriver.chrome.options import Options

token = 'token'
con = pymysql.connect(host='localhost', user='schoolnik', password='2987Kok_', database='school_bot')
cur = con.cursor()
cur.execute('create table IF NOT EXISTS users(id int primary key NOT NULL AUTO_INCREMENT, login varchar(100), password varchar(30), chat_id bigint, dn_id bigint, raspisanie varchar(100));')
keys = {}

bot = telebot.TeleBot(token=token)



def check(chat_id):
    cur.execute(f'SELECT id FROM users WHERE chat_id = {chat_id};')
    user = cur.fetchall()
    if user:
        return True
    else:
        bot.send_message(chat_id, 'Сначала войдите в профиль дневника!', reply_markup=get_markup(chat_id))
        return False


def rep_kav(text):
    if text:
        return text.replace("\'", '').replace("\"", '')
    else:
        return ''


def get_markup(chat_id):
    cur.execute(f'SELECT raspisanie FROM users WHERE chat_id = {chat_id};')
    user = cur.fetchall()
    if user:
        if user[0][0]:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            button1 = telebot.types.KeyboardButton(text="Расписание")
            button2 = telebot.types.KeyboardButton(text="Дз на завтра")
            button3 = telebot.types.KeyboardButton(text="Мои оценки")
            markup.add(button1).row(button2, button3)
            return markup
        else:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            button2 = telebot.types.KeyboardButton(text="Дз на завтра")
            button3 = telebot.types.KeyboardButton(text="Мои оценки")
            markup.row(button2, button3)
            return markup
    else:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        button1 = telebot.types.KeyboardButton(text="Вход в дневник.ру")
        return markup.add(button1)


def search(chat_id, school_id, user_id, dn):
    try:
        t2 = 0
        works = dn.get_work_types(school_id)
        while keys[str(chat_id)]:
            t1 = datetime.now()
            if t2:
                t = datetime.now() - t2
                old_marks = dn.get_person_marks(user_id, school_id, start_time=datetime.now() - timedelta(weeks=4) - t)
            else:
                t = timedelta(seconds=0)
                old_marks = dn.get_person_marks(user_id, school_id, start_time=datetime.now() - timedelta(weeks=4))
            time.sleep(60)
            t2 = datetime.now()
            marks = dn.get_person_marks(user_id, school_id, start_time=datetime.now() - timedelta(weeks=4) - timedelta(seconds=120) - (datetime.now() - t1 - t))
            if len(marks) > len(old_marks):
                for mark in marks:
                    if not (mark in old_marks):
                        date = ''
                        for i in mark['date']:
                            if i != 'T':
                                date += i
                            else:
                                break
                        work_type = ''
                        for work in works:
                            if mark['workType'] == work['id']:
                                work_type = work['title']
                                break
                        f'Вам поставили *{mark["textValue"]}* по предмету *{dn.get_lesson_info(mark["lesson"])["subject"]["name"]}*!\n\n_Дата:_  *{date.replace("-", ".")}*\n\n_Тип:_  *{work_type}*'


                        bot.send_message(chat_id, f'Вам поставили *{mark["textValue"]}* по предмету *{dn.get_lesson_info(mark["lesson"])["subject"]["name"]}*!\n\n_Дата:_  *{date.replace("-", ".")}*\n\n_Тип:_  *{work_type}*', reply_markup=get_markup(chat_id), parse_mode='Markdown')
    except:
        bot.send_message(chat_id, 'Что-то пошло не так!', reply_markup=get_markup(chat_id))
        keys[str(chat_id)] = False





@bot.message_handler(commands=['start'])
def start(message):
    if check(message.chat.id):
        bot.send_message(message.chat.id, 'Привет!', reply_markup=get_markup(message.chat.id))


@bot.message_handler(commands=['start_marks_search'])
def start_search(message):
    if check(message.chat.id):
        try:
            cur.execute(f'SELECT login, password, dn_id FROM users WHERE chat_id={message.chat.id};')
            user = cur.fetchall()[0]
            dn = dnevnik.DiaryAPI(user[0], user[1])
            a = True
            for th in threading.enumerate():
                if th.name == str(message.chat.id):
                    bot.send_message(message.chat.id, "Ваш поиск уже запущен! Если хотите остановить поиск:\n/stop_marks_search", reply_markup=get_markup(message.chat.id))
                    a = False
                    break
            if a:
                keys[str(message.chat.id)] = True
                thread = threading.Thread(target=search, args=(message.chat.id, dn.get_context()["schoolIds"][0], user[2], dn), name=str(message.chat.id))
                thread.start()
                bot.send_message(message.chat.id, "Запущен поиск оценок!", reply_markup=get_markup(message.chat.id))
        except:
             bot.send_message(message.chat.id, 'Что-то пошло не так!', reply_markup=get_markup(message.chat.id))



@bot.message_handler(commands=['stop_marks_search'])
def close_search(message):
    if check(message.chat.id):
        for th in threading.enumerate():
            if th.name == str(message.chat.id):
                keys[str(message.chat.id)] = False
                bot.send_message(message.chat.id, "Поиск остановлен!", reply_markup=get_markup(message.chat.id))


def get_password(message, login):
    if message.text:
        if message.text != 'Отмена🔙':
            try:
                login = rep_kav(login)
                password = rep_kav(message.text)
                dn = dnevnik.DiaryAPI(login=login, password=password)
                cur.execute(f'INSERT INTO users (login, password, chat_id, dn_id) VALUES ("{login}", "{password}", {message.chat.id}, {dn.get_context()["personId"]});')
                con.commit()
                bot.send_message(message.chat.id, f'Вы успешно зарегестрировались как {dn.get_context()["shortName"]}', reply_markup=get_markup(message.chat.id))
            except:
                bot.send_message(message.chat.id, 'Логин и пароль не подходят!', reply_markup=get_markup(message.chat.id))
        else:
            bot.send_message(message.chat.id, 'Вход отменен', reply_markup=get_markup(message.chat.id))
    else:
        bot.send_message(message.chat.id, 'Вход отменен', reply_markup=get_markup(message.chat.id))


def get_login(message):
    if message.text:
        if message.text != 'Отмена🔙':
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(telebot.types.KeyboardButton("Отмена🔙"))
            bot.send_message(message.chat.id, 'Введите ваш пароль от дневника.ру', reply_markup=markup)
            bot.register_next_step_handler(message, get_password, login=message.text)
        else:
            bot.send_message(message.chat.id, 'Вход отменен', reply_markup=get_markup(message.chat.id))
    else:
        bot.send_message(message.chat.id, 'Вход отменен', reply_markup=get_markup(message.chat.id))


@bot.message_handler(commands=['login'])
def login(message):
    cur.execute(f'SELECT id FROM users WHERE chat_id = {message.chat.id};')
    user = cur.fetchall()
    if user:
        bot.send_message(message.chat.id, "Вы уже зарегестрированы! Если хотите выйти /logout")
    else:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(telebot.types.KeyboardButton("Отмена🔙"))
        bot.send_message(message.chat.id, 'Введите ваш логин от дневника.ру', reply_markup=markup)
        bot.register_next_step_handler(message, get_login)





@bot.message_handler(commands=['logout'])
def logout(message):
    if check(message.chat.id):
        cur.execute(f'DELETE FROM users WHERE chat_id={message.chat.id};')
        con.commit()
        bot.send_message(message.chat.id, "Вы успешно вышли!", reply_markup=get_markup(message.chat.id))


def add_rasp(message):
    if message.text:
        if message.text == 'Отмена🔙':
            bot.send_message(message.chat.id, 'Добавление отменено', reply_markup=get_markup(message.chat.id))
        else:

            cur.execute(f'UPDATE users SET raspisanie = "{rep_kav(message.text)}" WHERE chat_id = {message.chat.id}')
            con.commit()
            bot.send_message(message.chat.id, 'Расписание добавлено', reply_markup=get_markup(message.chat.id))
    else:
        bot.send_message(message.chat.id, 'Добавление отменено', reply_markup=get_markup(message.chat.id))


@bot.message_handler(commands=['raspisanie'])
def raspisanie(message):
    if check(message.chat.id):
        cur.execute(f'SELECT raspisanie FROM users WHERE chat_id={message.chat.id};')
        user = cur.fetchall()[0]

        if user[0]:
            bot.send_message(message.chat.id, f"Расписание на завтра:\n{user[0]}\n\nСсылка на Дневник.ру\nhttps://dnevnik.ru/userfeed", reply_markup=get_markup(message.chat.id))
        else:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(telebot.types.KeyboardButton("Отмена🔙"))
            bot.send_message(message.chat.id, "Для добавления расписания отправьте ссылку", reply_markup=markup)
            bot.register_next_step_handler(message, add_rasp)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, '*Команды:*\n\n/login - вход в дневник.ру\n\n/raspisanie - добавление ссылки на расписание\n\n/logout - выход из аккаунта дневник.ру\n\n/start_marks_search - начать поиск оценок\n\n/stop_marks_search - остановить поиск оценок')


def send_files(dn, chat_id):
    try:
        t = dn.get_school_homework(dn.get_context()['schoolIds'][0], datetime.now(), datetime.now() + timedelta(days=1))
        if t['files']:
            for file in t['files']:
                rash = ''
                for i in ''.join(reversed(file['downloadUrl'])):
                    if i != '.':
                        rash += i
                    else:
                        break

                rash = ''.join(reversed(rash))
                resp = requests.get(file['downloadUrl'])
                with open(file['name'] + '.'+rash, 'wb') as fil:
                    fil.write(resp.content)
                    fil.close()
                bot.send_document(chat_id, open(file['name'] + '.' + rash, 'rb'), reply_markup=get_markup(chat_id))
                os.remove(os.getcwd() + f'/{file["name"]}.' + rash)
    except:
         bot.send_message(chat_id, 'Что-то пошло не так!', reply_markup=get_markup(chat_id))


@bot.message_handler()
def answer(message):
    if message.text == 'Вход в дневник.ру':
        login(message)
    else:
        if check(message.chat.id):
            if message.text == 'Расписание':
                raspisanie(message)
            elif message.text == 'Дз на завтра':
                try:
                    cur.execute('SELECT chat_id, login, password, dn_id FROM users;')
                    for user in cur.fetchall():
                        if user[0] == message.chat.id:
                            dn = dnevnik.DiaryAPI(login=user[1], password=user[2])
                            lessons_list = []
                            groups = []
                            for group in dn.get_person_groups_all(user[3]):
                                groups.append(group['id'])


                            for lesson in dn.get_group_lessons_info(dn.get_context()['groupIds'][0], datetime.now() + timedelta(days=1), datetime.now() + timedelta(days=1) + timedelta(seconds=2)):
                                if lesson['group'] in groups:
                                    homework = ''
                                    for work in lesson['works']:
                                        if work['text']:
                                            homework += work['text'].replace('\n', '').replace('\t', '') + ' '
                                    lessons_list.append({'number': lesson['number'], 'name': lesson['subject']['name'], 'id': lesson['id'], 'homework': homework})

                            message_s = "Дз на завтра:"
                            for lesson in lessons_list:
                                message_s += '\n\n' + '*' + lesson['name'] + ':*' + '  ' + '_' + lesson['homework'] + '_'
                            bot.send_message(message.chat.id, message_s, reply_markup=get_markup(message.chat.id), parse_mode="Markdown")
                            send_files(dn, message.chat.id)
                except:
                     bot.send_message(message.chat.id, 'Что-то пошло не так!', reply_markup=get_markup(message.chat.id))
            elif message.text == 'Мои оценки':
                try:
                    msg = bot.send_message(message.chat.id, 'Подождите...')
                    cur.execute(f'SELECT login, password FROM users WHERE chat_id={message.chat.id};')
                    user = cur.fetchall()[0]
                    dn = dnevnik.DiaryAPI(login=user[0], password=user[1])
                    us = dn.get_context()
                    if system() == 'Windows':
                        options = Options()
                        options.add_argument("--headless=new")
                        driver = webdriver.Chrome(options=options)
                        driver.set_window_size('2500', '3000')
                        driver.get("https://login.dnevnik.ru/login")
                        input_field = driver.find_element(By.CLASS_NAME, "login__body__input_login")
                        input_field.send_keys(user[0])
                        input_field = driver.find_element(By.ID, "password-field")
                        input_field.send_keys(user[1])
                        button = driver.find_element(By.CLASS_NAME, "login__submit")
                        button.click()
                        driver.get(f'https://dnevnik.ru/marks/school/{us["schoolIds"][0]}/student/{us["personId"]}/period')
                        time.sleep(1)
                        driver.execute_script("arguments[0].scrollIntoView(true);", driver.find_element(By.CLASS_NAME, 'Tamh1'))
                        time.sleep(1)
                        driver.find_element(By.CLASS_NAME, 'Tamh1').screenshot("screenshot.png")
                        driver.close()
                        driver.quit()
                    elif system() == "Linux":
                        display = Display(visible=False, size=(1600, 1000))
                        display.start()
                        driver = webdriver.Chrome()
                        driver.set_window_size('2500', '3000')
                        driver.get("https://login.dnevnik.ru/login")
                        input_field = driver.find_element(By.CLASS_NAME, "login__body__input_login")
                        input_field.send_keys("shufliknikolai")
                        input_field = driver.find_element(By.ID, "password-field")
                        input_field.send_keys("2987Kok_")
                        button = driver.find_element(By.CLASS_NAME, "login__submit")
                        button.click()
                        driver.get('https://dnevnik.ru/marks/school/1000016844863/student/1000024464183/period')
                        time.sleep(5)
                        driver.execute_script("arguments[0].scrollIntoView(true);", driver.find_element(By.CLASS_NAME, 'Tamh1'))
                        time.sleep(1)
                        driver.find_element(By.CLASS_NAME, 'Tamh1').screenshot("screenshot.png")
                        driver.close()
                        driver.quit()
                        display.stop()
                    path = os.getcwd()
                    if os.path.exists(path + '/screenshot.png'):
                        bot.send_photo(message.chat.id, open(path + '/screenshot.png', 'rb'), reply_markup=get_markup(message.chat.id))
                        bot.delete_message(message.chat.id, msg.message_id)
                        os.remove(path + '/screenshot.png')
                    else:
                        bot.send_message(message.chat.id, 'Что-то пошло не такt!', reply_markup=get_markup(message.chat.id))
                except:
                    bot.send_message(message.chat.id, 'Что-то пошло не так!', reply_markup=get_markup(message.chat.id))







def main():
    global bot
    while True:
        try:
            bot.infinity_polling()
        except:
            bot = telebot.TeleBot(token=token)

def do():
    bot.infinity_polling()

do()

import telebot;
from telebot import types
import requests
import json
# Импортируем библиотеку, соответствующую типу нашей базы данных
import sqlite3

#глобальные переменные
roleId = -1
roleName = ''
userId = -1
userName = ''
projectId = -1
projectName = ''
results = [] # выборка из базы
answer_results = [] # список сообщений
current_view_answer_index = -1 # переменная для запоминания индекса в answer_results

TOKEN = "915222841:AAH7C7xrsDp6vVg17c5H7OCKi9ftDFNVVEY"
bot = telebot.TeleBot(TOKEN);

# Создаем соединение с нашей базой данных
# В нашем примере у нас это просто файл базы
conn = sqlite3.connect('TelegBot.sqlite',check_same_thread=False)
# Создаем курсор - это специальный объект который делает запросы и получает их результаты
cursor = conn.cursor()

#кнопка Далее у Разработчика при просмотре сообщений
view_next_keyboard = types.InlineKeyboardMarkup()
callback_button_next = types.InlineKeyboardButton(text="Далее",callback_data="view-next-answer")
view_next_keyboard.add(callback_button_next)

#кнопки Принять и перейти и Удалить у Администратора при просмотре сообщений
view_admin_keyboard = types.InlineKeyboardMarkup()
callback_button_approve = types.InlineKeyboardButton(text="Принять и перейти",callback_data="view-approve-answer")
callback_button_remove = types.InlineKeyboardButton(text="Удалить",callback_data="view-remove-answer")
view_admin_keyboard.add(callback_button_approve)
view_admin_keyboard.add(callback_button_remove)

#обработчик команды /start
@bot.message_handler(commands=["start"])
def welcome(message):
	results = setValuesFromDB(message.chat.id)
	#len - функци я количества элементов в листе
	if len(results) != 0:
		# заполняем глобальные переменные данными
		setUserData(results)
		keyboard = types.InlineKeyboardMarkup()
		#Добавляем колбэк-кнопку
		callback_button_yes = types.InlineKeyboardButton(text="Да", callback_data="yes-"+roleName)
		callback_button_no = types.InlineKeyboardButton(text="Нет", callback_data="no-"+roleName)
		keyboard.add(callback_button_yes)
		keyboard.add(callback_button_no)
		if roleName == 'Customer':
			bot.send_message(message.chat.id, "Здравствуй "+ userName +"(роль " + roleName+ ", проект " + projectName + "), хочешь оставить новые сообщения для разработчиков своего проекта?", reply_markup=keyboard)
		elif roleName == 'Developer':
			bot.send_message(message.chat.id, "Здравствуй "+ userName +"(роль " + roleName+ ", проект " + projectName + "), тебе показать новые сообщения, оставленные для твоего проекта, если они есть?", reply_markup=keyboard)
		else:
			bot.send_message(message.chat.id, "Здравствуй "+ userName +"(роль " + roleName+ "), тебе показать новые сообщения?", reply_markup=keyboard)
	else:
		bot.send_message(message.chat.id, "Извините, но вас нет в базе данных, вам доступ запрещен")

#срабатывает при нажатии на кнопку
#В библиотеке pyTelegramBot Api есть декоратор @bot.callback_query_handler, который передает объект CallbackQuery во вложенную функцию.
@bot.callback_query_handler(func=lambda call: True)
def iq_callback(query):
	global current_view_answer_index # переменная для запоминания индекса в answer_results
	data = query.data
	if data.startswith('yes'):
		get_yes_callback(query)
	elif data == 'view-next-answer':
		if len(answer_results)>(current_view_answer_index+1):
			current_view_answer_index = current_view_answer_index+1
			# вывод  следующего сообщения из списка
			bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text=answer_results[current_view_answer_index][1],reply_markup=view_next_keyboard)
			cursor.execute("update Answers set IsNew = 0 where AnswerId =" + str(answer_results[current_view_answer_index][0]))
			conn.commit()
		else:
			bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="Все, ты просмотрел все сообщения")
	elif data == 'view-approve-answer' or data == 'view-remove-answer':
		if len(answer_results) >= (current_view_answer_index+1):
			if data == 'view-approve-answer':
				strSql = "update Answers set IsApproved = 1 where AnswerId =" + str(answer_results[current_view_answer_index][0])
			else:
				strSql = "update Answers set IsApproved = 0 where AnswerId =" + str(answer_results[current_view_answer_index][0])
			cursor.execute(strSql)
			conn.commit()
			current_view_answer_index = current_view_answer_index + 1
			if len(answer_results) > current_view_answer_index:
				#вывод  следующего сообщения из списка
				bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id,text=answer_results[current_view_answer_index][1], reply_markup=view_admin_keyboard)
			else:
				bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="Все, ты просмотрел все сообщения")
	else:
		bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="До свидания!")


#обработчик кнопки ДА у ЛЮБОЙ роли
def get_yes_callback(query):
	results = setValuesFromDB(query.message.chat.id)
	# len - функци я количества элементов в листе
	if len(results) != 0:
		# заполняем глобальные переменные данными
		setUserData(results)
		if roleName == 'Admin':
			# убираем кнопки ДА НЕТ
		    bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="Здравствуй "+ userName +"(роль " + roleName+ "), тебе показать новые сообщения?")
		    strSql = "select an.AnswerId, an.Text from Answers an where an.IsNew = 1 and an.IsApproved is NULL"
		    view_answers(query, strSql, roleName)
		elif roleName == 'Developer':
			# убираем кнопки ДА НЕТ
		    bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="Здравствуй "+ userName +"(роль " + roleName+ ", проект " + projectName + "), тебе показать новые сообщения, оставленные для твоего проекта, если они есть?")
		    strSql = "select an.AnswerId, an.Text from Answers an inner join User us on an.FromUserId  = us.UserId inner join Role r on r.RoleId = us.RoleId where us.ProjectId = '" + str(projectId) + "' and r.Name = 'Customer' and an.IsNew = 1 and an.IsApproved = 1"
		    view_answers(query, strSql, roleName)
		elif roleName == 'Customer':
			#убираем кнопки ДА НЕТ
		    bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text="Здравствуй "+ userName +"(роль " + roleName+ ", проект " + projectName + "), хочешь оставить новые сообщения для разработчиков своего проекта?")
		    bot.send_message(query.message.chat.id, "Вводи новые сообщения. Каждое сообщение считается законченным после отправки. По окончании ввода введи /end")
	else:
		bot.send_message(message.chat.id, "Извините, но вас нет в базе данных, вам доступ запрещен")

def view_answers(query, strSql, roleName):
	global answer_results
	global current_view_answer_index

	cursor.execute(strSql)
	# Получаем результат сделанного запроса, список сообщений, для Админа один, для Девелопера другой
	answer_results = cursor.fetchall()
	if len(answer_results) != 0:
		if roleName == "Developer":
			bot.send_message(query.message.chat.id, answer_results[0][1], reply_markup=view_next_keyboard)
			current_view_answer_index = 0
			cursor.execute("update Answers set IsNew = 0 where AnswerId =" + str(answer_results[0][0]))
			conn.commit()
		elif roleName == "Admin":
			bot.send_message(query.message.chat.id, answer_results[0][1], reply_markup=view_admin_keyboard)
			current_view_answer_index = 0
	else:
		bot.send_message(query.message.chat.id, "Чувак, извини, но ничего нет")

#обработчик введенного какого-то текста
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
	global roleName
	results = setValuesFromDB(message.chat.id)
	# len - функци я количества элементов в листе
	if len(results) != 0:
		if roleName == 'Customer':
			if message.text != '/end':
				#запись в БД сообщений от заказчика
				cursor.execute("insert into Answers values (Null, '" + message.text + "', 1, " + str(userId) + ", Null) ")
				conn.commit()
			else:
				bot.send_message(message.chat.id, "Ввод закончен, до свидания!")
				roleName = ''
	else:
		bot.send_message(message.chat.id, "Извините, но вас нет в базе данных, вам доступ запрещен")


def setValuesFromDB(from_user_id):
	# Делаем SELECT запрос к базе данных, используя обычный SQL-синтаксис
	cursor.execute(
		"select u.UserId, r.RoleId, r.Name, u.Name, u.ProjectId from User u inner join Role r on u.RoleId = r.RoleId where Identification  = '" + str(
			from_user_id) + "'")

	# Получаем результат сделанного запроса
	results = cursor.fetchall()
	return results

def setUserData(results):
	global roleId
	global roleName
	global userId
	global userName
	global projectId
	global projectName

	userId = results[0][0]
	roleId = results[0][1]
	roleName = results[0][2]
	userName = results[0][3]
	projectId = results[0][4]

	# вытаскиваем имя проекта, для всех кроме Админа
	if projectId is not None:
		cursor.execute("select Name from Project where ProjectId  = '" + str(projectId) + "'")
		resultsPr = cursor.fetchall()
		projectName = resultsPr[0][0]
	else:
		projectName = ''



@server.route('/' + tokenBot.TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://test-new-new.herokuapp.com/' + tokenBot.TOKEN)
    return "!", 200

if __name__ == '__main__':
	server.debug = True
	server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

import asyncio
import logging
from aiogram import Bot, Dispatcher#, types
from aiogram.filters.command import Command
import aiosqlite
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
import nest_asyncio
import quiz_questions
quiz_data = quiz_questions.quiz_data
nest_asyncio.apply()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# t.me/Quantum_Quiz_bot
API_TOKEN = '7093775296:AAGvD6WjQW_ejYHK8zy9Jm_mRTC_WPFLEFo'
DB_NAME = 'quantum_quiz_bot.db'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик одну кнопку
    builder.add(types.KeyboardButton(text="Начать игру"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Привет! Готов играть в квиз? Введите /quiz, чтобы начать.",
                         reply_markup=builder.as_markup(resize_keyboard=True))


# Хэндлер на команду /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз!")
    # Запускаем новый квиз
    await new_quiz(message)


#======== Логика квиза ========
async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index, 0)
    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)


async def get_question(message, user_id):
    # Запрашиваем из базы текущий индекс для вопроса и текущий счет пользователя
    #current_question_index = await get_quiz_index(user_id)
    (current_question_index, current_score) = await get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса
    correct_index = quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts, opts[correct_index])
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


def generate_options_keyboard(answer_options, right_answer):
  # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем 4 Inline кнопки, а точнее Callback-кнопки
    for option in answer_options:
        # В колбэк-данных каждой кнопки передаем: ответ_верный/неверный:<Текст_ответа>
        callback_data = "answer_" + ("right" if option == right_answer else "wrong") + ":" + option
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            # Если ответ верный сформируется колбэк-запрос с данными 'right_answer'
            # Если ответ неверный сформируется колбэк-запрос с данными 'wrong_answer'
            callback_data=callback_data)
        )
    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()


#@dp.callback_query(F.data == "right_answer")
@dp.callback_query(F.data.startswith("answer_"))
async def right_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None,
    )

    # Получение текущего вопроса для данного пользователя и его счета
    # Запрашиваем из базы текущий индекс для вопроса и текущий счет пользователя
    (current_question_index, current_score) = await get_quiz_index(callback.from_user.id)

    # Достаем из callback.data текст выбранного ответа и признак верного ответа
    selected_answer_text = callback.data.split("_")[1].split(":")[1]
    is_right_answer = callback.data.split("_")[1].split(":")[0]

    if is_right_answer == "right":
        # Отправляем в чат текст выбранного ответа и сообщение, что ответ верный
        await callback.message.answer(selected_answer_text)
        await callback.message.answer("Верно!")
        current_score += 1
    else:
        correct_option = quiz_data[current_question_index]['correct_option']
        # Отправляем в чат текст выбранного ответа и сообщение об ошибке с указанием верного ответа
        await callback.message.answer(selected_answer_text)
        await callback.message.answer(
            f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, current_score)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!\n"
            + "Ваш счет: " + str(current_score) + " из " + str(len(quiz_data)))
        # Выбод статисики
        stat_list = await get_quiz_statistics(callback.from_user.id)
        if len(stat_list) > 0:
            await callback.message.answer("Статистика по игрокам:\n")
            stat_str = ""
            for player in stat_list:
                #stat_str += "Игрок " + str(await get_username(player[0])) + ": " + str(player[1]) + " очков\n"
                stat_str += "Игрок " + str(player[0]) + ": " + str(player[1]) + " очков\n"
            await callback.message.answer(stat_str)

#========== / ==========


#========== БД ==========
# Создаем таблицу базы данных для хранения номера вопроса, на котором остановился пользователь,
# и количества очков, набранных за последнюю игру
async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Выполняем SQL-запрос к базе данных
        await db.execute('''CREATE TABLE IF NOT EXISTS 
            quiz_state (
            user_id INTEGER PRIMARY KEY, 
            question_index INTEGER, 
            last_score INTEGER
            )''')
        # Сохраняем изменения
        await db.commit()


async def update_quiz_index(user_id, index, score):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, last_score) VALUES (?, ?, ?)',
                         (user_id, index, score))
        # Сохраняем изменения
        await db.commit()


async def get_quiz_index(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index, last_score FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return (results[0], results[1], )
            else:
                return 0


async def get_quiz_statistics(user_id):
    result_list = []
    # Подключаемся к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем записи для заданного пользователя
        async with db.execute('SELECT user_id, last_score FROM quiz_state ORDER BY last_score') as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            while results is not None:
                result_list.append([results[0], results[1]])
                results = await cursor.fetchone()
            return result_list
#========== / ==========


# Запуск процесса поллинга новых апдейтов
async def main():
    # Запускаем создание таблицы базы данных
    await create_table()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

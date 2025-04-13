#import aiosqlite
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import pool, execute_update_query, execute_select_query
from quiz_questions import quiz_data

#DB_NAME = 'quantum_quiz_bot.db'


# Выдаёт набор кнопок с вариантами ответов на вопрос
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
            callback_data=callback_data)
        )
    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()


#======== Логика квиза ========
async def new_quiz(message):
    # получаем id и имя пользователя, отправившего сообщение
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index, 0, user_name)
    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)



async def get_question(message, user_id):
    # Запрашиваем из базы текущий индекс для вопроса и текущий счет пользователя
    #if YDB_ENDPOINT == None:
    #    (current_question_index, current_score) = await get_quiz_index_aio(user_id)
    #else:
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



async def show_statistics(msg_or_clbk):
    user_id = msg_or_clbk.from_user.id
    is_message = (type(msg_or_clbk) == types.Message)
    stat_list = await get_quiz_statistics(user_id)
    if len(stat_list) > 0:
        stat_str = ""
        for player in stat_list:
            stat_str += str(player[0]) + ": " + str(player[1]) + " очков\n"
        if is_message:
            await msg_or_clbk.answer("Статистика по игрокам:\n" + stat_str)
        else:
            await msg_or_clbk.message.answer("Статистика по игрокам:\n" + stat_str)

#========== / ==========


#========== Работа с Yandex БД ==========
async def update_quiz_index(user_id, question_index, score, user_name):
    # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
    set_quiz_state = f"""
        DECLARE $user_id AS Uint64;
        DECLARE $question_index AS Uint64;
        DECLARE $last_score AS Uint64;
        DECLARE $user_name AS Utf8;

        UPSERT INTO `quiz_state` (`user_id`, `question_index`, `last_score`, `user_name`)
        VALUES ($user_id, $question_index, $last_score, $user_name);
    """

    execute_update_query(
        pool,
        set_quiz_state,
        user_id=user_id,
        question_index=question_index,
        last_score=score,
        user_name=str(user_name),
    )


async def get_quiz_index(user_id):
    # Получаем запись для заданного пользователя
    get_user_index = f"""
        DECLARE $user_id AS Uint64;

        SELECT question_index, last_score
        FROM `quiz_state`
        WHERE user_id == $user_id;
    """
    results = execute_select_query(pool, get_user_index, user_id=user_id)

    if len(results) == 0:
        return (0, 0)
    if results[0]["question_index"] is None:
        return (0, 0)
    #return results[0]["question_index"]
    return (results[0]["question_index"], results[0]["last_score"],)


async def get_quiz_statistics(user_id):
    result_list = []

    get_users_score = f"""
        SELECT user_id, last_score, user_name
        FROM `quiz_state`
        ORDER BY last_score DESC
    """
    results = execute_select_query(pool, get_users_score)

    if len(results) == 0:
        return []
    if results[0]["user_id"] is None:
        return []

    for i in range(len(results)):
        if results[i]["user_id"] is None:
            continue
        else:
            if results[i]["user_name"] is None:
                user_name = results[i]["user_id"]
            else:
                user_name = results[i]["user_name"]

            result_list.append([user_name, results[i]["last_score"]])

    return result_list

#========== / ==========


#========== Работа с файловой БД на aiosqlite ==========
# Создаем таблицу базы данных для хранения номера вопроса, на котором остановился пользователь,
# и количества очков, набранных за последнюю игру
async def create_table_aio():
    return
#   Создаем соединение с базой данных (если она не существует, то она будет создана)
#     async with aiosqlite.connect(DB_NAME) as db:
#         # Выполняем SQL-запрос к базе данных
#         await db.execute('''CREATE TABLE IF NOT EXISTS
#             quiz_state (
#             user_id INTEGER PRIMARY KEY,
#             question_index INTEGER,
#             last_score INTEGER
#             )''')
#         #user_name STRING,
#         # Сохраняем изменения
#         await db.commit()
#
#
# async def update_quiz_index_aio(user_id, index, score):
#     # Создаем соединение с базой данных (если она не существует, она будет создана)
#     async with aiosqlite.connect(DB_NAME) as db:
#         # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
#         await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, last_score) VALUES (?, ?, ?)',
#                          (user_id, index, score))
#         # Сохраняем изменения
#         await db.commit()
#
#
# async def get_quiz_index_aio(user_id):
#     # Подключаемся к базе данных
#     async with aiosqlite.connect(DB_NAME) as db:
#         # Получаем запись для заданного пользователя
#         async with db.execute('SELECT question_index, last_score FROM quiz_state WHERE user_id = (?)',
#                               (user_id,)) as cursor:
#             # Возвращаем результат
#             results = await cursor.fetchone()
#             if results is not None:
#                 return (results[0], results[1],)
#             else:
#                 return ()
#
#
# async def get_quiz_statistics_aio(user_id):
#     result_list = []
#     # Подключаемся к базе данных
#     async with aiosqlite.connect(DB_NAME) as db:
#         # Получаем записи для заданного пользователя
#         async with db.execute('SELECT user_id, last_score FROM quiz_state ORDER BY last_score') as cursor:
#             # Возвращаем результат
#             results = await cursor.fetchone()
#             while results is not None:
#                 result_list.append([results[0], results[1]])
#                 results = await cursor.fetchone()
#             return result_list
#========== / ==========

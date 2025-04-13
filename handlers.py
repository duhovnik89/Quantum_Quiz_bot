from aiogram import types, Dispatcher, F, Router
#from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
#from database import YDB_ENDPOINT
from quiz_questions import quiz_data
from service_functions import get_question, new_quiz, get_quiz_index, update_quiz_index, show_statistics
#from service_functions import get_quiz_index_aio, update_quiz_index_aio,

router = Router()


# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик одну кнопку
    builder.add(types.KeyboardButton(text="Начать игру"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Привет, " + message.from_user.full_name + "! Готов играть в квиз? Введи /quiz или нажми 'Начать игру'.",
                         reply_markup=builder.as_markup(resize_keyboard=True))


# Хэндлер на команду /quiz
@router.message(F.text == "Начать игру")
@router.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз!")

    # Отправляем в чат картинку перед началом квиза
    img_url = "https://storage.yandexcloud.net/quantum-imgs/Quantum_desc_img.jpg"
    img_id = await message.answer_photo(photo=img_url, caption="Раунд 1")

    await new_quiz(message)


# Хэндлер на команду /statistics
@router.message(Command("statistics"))
async def cmd_statistics(message: types.Message):
    await show_statistics(message)


@router.callback_query(F.data.startswith("answer_"))
async def right_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None,
    )

    # Получение текущего вопроса для данного пользователя и его счета
    # Запрашиваем из базы текущий индекс для вопроса и текущий счет пользователя
    #if YDB_ENDPOINT == None:
    #    (current_question_index, current_score) = await get_quiz_index_aio(callback.from_user.id)
    #else:
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
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    #if YDB_ENDPOINT == None:
    #    await update_quiz_index_aio(callback.from_user.id, current_question_index, current_score)
    #else:
    await update_quiz_index(user_id, current_question_index, current_score, user_name)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!\n"
                                      + "Ваш счет: " + str(current_score) + " из " + str(len(quiz_data)))
        # Вывод статистики
        await show_statistics(callback)
import asyncio
import logging
from aiogram import Bot, Dispatcher
from service_functions import create_table_aio
import nest_asyncio
nest_asyncio.apply()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# t.me/Quantum_Quiz_bot
API_TOKEN = '7736539085:AAGoV32t_3j5960cAR88vFjmkHXAARmEDn8'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()


# Запуск процесса поллинга новых апдейтов
async def main():
    # Запускаем создание таблицы базы данных
    await create_table_aio()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

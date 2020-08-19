import config
import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from sqlighter import SQLighter
from stopgame import StopGame

# set the level of logs
logging.basicConfig(level=logging.INFO)

# initialize the bot
bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot)

# initialize the connection to the database
db = SQLighter('db.db')

# initialize the parser
sg = StopGame('lastkey.txt')

# Subscription activation command
@dp.message_handler(commands=['subscribe'])
async def subscribe(message: types.Message):
	if(not db.subscriber_exists(message.from_user.id)):
		# if the user is not in the database, add him
		db.add_subscriber(message.from_user.id)
	else:
		# if it already exists, then just update its subscription status
		db.update_subscription(message.from_user.id, True)
	
	await message.answer("Вы успешно подписались на рассылку!\nЖдите, скоро выйдут новые обзоры и вы узнаете о них первыми =)")

# Unsubscribe command
@dp.message_handler(commands=['unsubscribe'])
async def unsubscribe(message: types.Message):
	if(not db.subscriber_exists(message.from_user.id)):
		# if the user is not in the database, add him with an inactive subscription (remember)
		db.add_subscriber(message.from_user.id, False)
		await message.answer("Вы итак не подписаны.")
	else:
		# if it already exists, then just update its subscription status
		db.update_subscription(message.from_user.id, False)
		await message.answer("Вы успешно отписаны от рассылки.")

# check for new games and send mailings
async def scheduled(wait_for):
	while True:
		await asyncio.sleep(wait_for)

		# checking for new games
		new_games = sg.new_games()

		if(new_games):
			# if there are games, turn the list over and iterate
			new_games.reverse()
			for ng in new_games:
				# parse info about the new game
				nfo = sg.game_info(ng)

				# get a list of bot subscribers
				subscriptions = db.get_subscriptions()

				# sending news to everyone
				with open(sg.download_image(nfo['image']), 'rb') as photo:
					for s in subscriptions:
						await bot.send_photo(
							s[1],
							photo,
							caption = nfo['title'] + "\n" + "Оценка: " + nfo['score'] + "\n" + nfo['excerpt'] + "\n\n" + nfo['link'],
							disable_notification = True
						)
				
				# update key
				sg.update_lastkey(nfo['id'])

# start long polling
if __name__ == '__main__':
	dp.loop.create_task(scheduled(300)) # (5 min)
	executor.start_polling(dp, skip_updates=True)
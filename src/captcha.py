import base64
from io import BytesIO

import aiohttp
import pytesseract
from PIL import Image

CAPTCHA_URL = 'http://tsdaucap.bacninh.edu.vn/getcaptcha'


async def get_captcha(client: aiohttp.ClientSession, log) -> dict[str, str]:
	log('Pulling new captcha...')
	res = await client.get(CAPTCHA_URL)
	return await res.json()


async def solve_captcha(client: aiohttp.ClientSession, log) -> dict[str, str]:
	text = ''
	time = ''

	while len(text) != 4:
		captcha = await get_captcha(client, log)
		time = captcha['time']

		data = base64.b64decode(captcha['image'])
		img = Image.open(BytesIO(data))

		text = pytesseract.image_to_string(
			img, config='--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
		).strip()

	return {'time': time, 'text': text}

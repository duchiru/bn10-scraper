import aiohttp
from bs4 import BeautifulSoup

AUTH_URL = 'https://tsdaucap.bacninh.edu.vn/tra-cuu-ket-qua-tuyen-sinh-10-bac-ninh'
RESULT_URL = 'https://tsdaucap.bacninh.edu.vn/TraCuu/KetQuaTraCuuTuyenSinh10BacNinh'


class CaptchaException(Exception):
	pass


class IdException(Exception):
	pass


async def get_result_key(
	client: aiohttp.ClientSession, id: str, token: str, captcha: dict[str, str]
):
	res = await client.post(
		AUTH_URL,
		headers={
			'Requestverificationtoken': token,
			'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
		},
		data=f'MA_CAP_HOC=04&MA_HOC_SINH={id}&CaptchaTime={captcha["time"]}&CaptchaInput={captcha["text"]}',
	)

	json = await res.json()

	if json['message'] == 'Sai mã bảo vệ.':
		raise CaptchaException()
	elif json['message'] == 'Không tìm thấy hồ sơ thí sinh, vui lòng kiểm tra lại.':
		raise IdException()

	return json['key']


async def get_final_result(client: aiohttp.ClientSession, key: str) -> list[str]:
	res = await client.get(RESULT_URL, params={'key': key})
	html = BeautifulSoup(markup=await res.text(), features='html.parser')

	result = []

	rows = html.find_all('tr')
	for row in rows:
		try:
			result.append(list(row.children)[3].text)  # type: ignore
		except IndexError:
			pass

	return result


async def get_result(client: aiohttp.ClientSession, id: str, token: str, captcha: dict[str, str]):
	key = await get_result_key(client, id, token, captcha)
	return await get_final_result(client, key)

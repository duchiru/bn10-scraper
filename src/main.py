import asyncio
import sqlite3
import threading

import aiohttp
from bs4 import BeautifulSoup

from captcha import solve_captcha
from result import CaptchaException, IdException, get_result

ROOT_URL = 'https://tsdaucap.bacninh.edu.vn/tra-cuu-ket-qua-tuyen-sinh-bac-ninh'

MAX_SCHOOL_ID = 23  # 22 schools numbered from 02 to 23


async def extract_verification_token(client: aiohttp.ClientSession, log) -> str:
	log('Pulling verification token...')

	res = await client.get(ROOT_URL)
	html = BeautifulSoup(markup=await res.text(), features='html.parser')
	token = html.find('input', {'name': '__RequestVerificationToken'}).attrs['value']  # type: ignore
	return str(token)


c = threading.Condition()
results = []


async def worker(school_id):
	global results

	client = aiohttp.ClientSession()
	SCHOOL_ID_STR = ('0' if school_id < 10 else '') + str(school_id)

	def log(msg):
		print(f'[THREAD {SCHOOL_ID_STR}] {msg}')

	token = await extract_verification_token(client, log)
	captcha = await solve_captcha(client, log)

	current_student_id = 1
	school_result = []

	while True:
		STUDENT_ID_STR = str(current_student_id)
		STUDENT_ID_STR = '0' * (4 - len(STUDENT_ID_STR)) + STUDENT_ID_STR

		COMBINED_ID = SCHOOL_ID_STR + STUDENT_ID_STR

		try:
			log(f'Pulling result for id: {COMBINED_ID}')

			result = await get_result(client, COMBINED_ID, token, captcha)

			school_result.append(result)

			current_student_id += 1
		except CaptchaException:
			captcha = await solve_captcha(client, log)
		except IdException:
			break

	c.acquire()
	results.extend(school_result)
	c.release()

	await client.close()


def main():
	db = sqlite3.connect('output.db')

	cursor = db.cursor()

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS tong_hop (
    	so_bao_danh TEXT PRIMARY KEY,
    	ho_va_ten TEXT,
    	gioi_tinh TEXT,
    	ngay_sinh TEXT,
      noi_sinh TEXT,
      lop TEXT,
      truong_cuoi_cap TEXT,
      truong_nv1 TEXT,
      diem_uu_tien TEXT,
      diem_khuyen_khich TEXT,
      ngu_van TEXT,
      tieng_anh_tu_luan TEXT,
      tieng_anh_trac_nghiem TEXT,
      tong_tieng_anh TEXT,
      toan_tu_luan TEXT,
      toan_trac_nghiem TEXT,
      toan_tong TEXT,
      tong_diem_dai_tra TEXT,
      diem_mon_chuyen TEXT,
      tong_diem_chuyen TEXT
    );
		""")

	current_school_id = 2

	threads = []
	while current_school_id <= MAX_SCHOOL_ID:
		threads.append(threading.Thread(target=asyncio.run, args=(worker(current_school_id),)))

		current_school_id += 1

	for thread in threads:
		thread.start()

	for thread in threads:
		thread.join()

	cursor.executemany(
		'INSERT INTO tong_hop (so_bao_danh, ho_va_ten, gioi_tinh, ngay_sinh, noi_sinh, lop, truong_cuoi_cap, truong_nv1, diem_uu_tien, diem_khuyen_khich, ngu_van, tieng_anh_tu_luan, tieng_anh_trac_nghiem, tong_tieng_anh, toan_tu_luan, toan_trac_nghiem, toan_tong, tong_diem_dai_tra, diem_mon_chuyen, tong_diem_chuyen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
		results,
	)

	db.commit()


if __name__ == '__main__':
	main()

import telegram
import asyncio
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

import requests
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urlparse
from urllib.parse import parse_qsl
import sqlite3
import os
from fake_useragent import UserAgent
from time import sleep

if __debug__:
    import pandas as pd

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def is_date(string):
    format = "%Y-%m-%d"
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        datetime.datetime.strptime(string, format)
        return True

    except ValueError:
        return False

class botAgent:
    def __init__(self):
        self.conn, self.cur = self.connectDB()

        idTxt = "id_test.txt" if __debug__ else "id.txt"
        self.telBot, self.chatId = self.connectTelBot("token.ini", idTxt)

        self.FIDDLER = False
        if __debug__:
            if self.FIDDLER:
                self.proxies, self.verify = self.fiddlerSet()
    
    def fiddlerSet(self):
            proxies = {"http": "http://127.0.0.1:8888", "https": "http:127.0.0.1:8888"}
            verify = r"FiddlerRoot.pem"

            return proxies, verify

    def connectTelBot(self, tokenTxt: str, idTxt: str):
        with open(tokenTxt, 'r') as f:
            my_token = str(f.read()).strip() # 토큰을 설정해 줍니다.
            telBot = ApplicationBuilder().token(my_token).build()  # 봇 어플리케이션 오브젝트 생성.
            with open(idTxt, 'r') as f:
                chatId = int(f.read())
        
        return telBot, chatId
    
    def connectDB(self):
        # db 연결
        if __debug__:
            conn = sqlite3.connect('notice_test.db')
        else:
            conn = sqlite3.connect('notice.db')

        # (최초 실행 시) 테이블 생성
        cur = conn.cursor()
        try:
            cur.execute('''CREATE TABLE posts(id INT, title TEXT, link TEXT, cat TEXT, date TEXT, UNIQUE(id, cat))''')
        except:
            pass

        return conn, cur
    
    async def runBot(self):
        try:
            if __debug__:
                if not self.FIDDLER:
                    await self.dorm_notice_init_new()
                    await self.coi_notice()
                    await self.studyabroad()
                await self.portal()
                link = 'https://telegram.org/blog/link-preview#:~:text=Once%20you%20paste%20a%20URL,now%20shown%20for%20most%20websites.'
                link2 = 'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no=40659&s_type=1&s_text='
                display_data = pd.read_sql_query("SELECT * FROM posts", self.conn)
                print(display_data)
            else:
                await self.dorm_notice_init_new()
                await self.coi_notice()
                await self.studyabroad()
                await self.portal()
        finally:
            self.conn.commit()
            self.conn.close()
    
    async def dorm_notice_init(self):
        dorm_list = {'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice2': 'dorm-total',
                    'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice': 'dorm-oldgik',
                    'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice1': 'dorm-newgik'}
        for dorm_key in dorm_list.keys():
            await self.dorm_notice(dorm_key, dorm_list[dorm_key])

    async def dorm_notice_init_new(self):
        dorm_list = {'https://dorm.korea.ac.kr/front/board/1/post': 'dorm-total',}
        for dorm_key in dorm_list.keys():
            await self.dorm_notice_new(dorm_key, dorm_list[dorm_key])


    def get_post_id_from_javascript(self, href):
        post_id = int(href.split("'")[1])
        return post_id

    async def dorm_notice(self, url, cat):
        response = requests.get(url)
        category = {'dorm-total': '안암학사 - 전체공지', 'dorm-oldgik': '안암학사 - 학생동공지', 'dorm-newgik': '안암학사 - 프런티어관공지'}

        soup = BeautifulSoup(response.content.decode('euc-kr', 'replace'), "html.parser")

        tr_list = soup.select(
            'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr')

        for tr in tr_list:  # 각 게시글 당
            td_list = tr.select('td')  # td 리스트 생성
            for td in td_list:
                # 글 제목, id, 링크 가져오기
                a = td.find('a')
                try:
                    href = a.get('href')
                except Exception:
                    href = ''
                if 'javascript:viewBoard(document.BoardForm' in href:
                    title = a.text
                    post_id = self.get_post_id_from_javascript(href)
                    link = f'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no={post_id}&s_type=1&s_text='

                # 게시일 가져오기
                if is_date(td.text):
                    date = td.text

            try:
                if post_id:
                    post = [post_id, title, link, cat, date]
                    if __debug__:
                        self.print_info(post)
                    post_id = await self.post_id_validate(category, post)  # 이전 id 초기화
            except NameError:  # post_id를 가져오지 못 했을 때
                pass

    async def dorm_notice_new(self, url, cat):
        response = requests.get(url)
        category = {}

        soup = BeautifulSoup(response.content, "html.parser")

        tr_list = soup.select(
            'section > div > article.right-content.content_layout_area')
        tr_list = tr_list[0].select('section > div > article:nth-child(3) > table > tbody > tr')

        for tr in tr_list:  # 각 게시글 당
            td_title = tr.find('td', {'class': 'title'})
            td_date = tr.find('td', {'class': 'date'})

            cat = tr.select('td:nth-child(2) > p')[0].text
            if cat:
                cat = f'안암학사 - {cat}'
            else:
                cat = '안암학사 - 전체'

            if cat not in category.keys():
                category[cat] = cat

            a = td_title.find('a')
            href = a.get('href')
            title = a.text
            date = td_date.text
            post_id = os.path.split(href)[1][0:-1] # ? 제외

            link = f'{url}/{post_id}?'

            try:
                if post_id:
                    post = [post_id, title, link, cat, date]
                    if __debug__:
                        self.print_info(post)
                    post_id = await self.post_id_validate(category, post)  # 이전 id 초기화
            except NameError:  # post_id를 가져오지 못 했을 때
                pass

    async def post_id_validate(self,category, post):
        self.cur.execute(f'''SELECT id FROM posts WHERE cat = '{post[3]}' AND id = {post[0]} ''')  # 테이블에서 데이터 선택하기
        id = self.cur.fetchone()
        if id is None:  # 데이터베이스에 id가 없을 경우
            await self.telBotSend(category[post[3]], post[1], post[2], post[4])
            self.cur.execute('''INSERT OR IGNORE INTO posts VALUES(?,?,?,?,?)''',
                        (post[0], post[1], post[2], post[3], post[4]))
        else:
            if __debug__:
                print(f"id {post[0]} 중복\n")
        return 0

    async def telBotSend(self, cat, title, link, date):
        title = title.replace('&', '&amp;')
        title = title.replace('<', '&lt;').replace('>','&gt;')
        text = f"""
        <b>{cat}</b>

    <b>제목</b> {title}
    <b>게시일</b> {date}"""

        is_portal = cat.find('포털')
        if is_portal != -1:
            text += f'\n\n<a href="{link}">포털 바로가기</a>'
        else:
            text += f'\n\n<a href="{link}">게시글 바로가기</a>'

        while True:
            try:
                await self.telBot.bot.send_message(chat_id=self.chatId, text=text, parse_mode="html") #제목에 <> 등 들어가면 문제 발생함
                break
            except Exception as tel_error:
                print(f'Error: {tel_error}, waiting...')
                if 'Flood control exceeded' in str(tel_error):
                    flood = str(tel_error).split(' ')[-2]
                    sleep(float(flood))
                continue

    async def coi_notice(self):
        URL_GENERAL = 'https://info.korea.ac.kr/info/board/notice_under.do'
        URL_EVENT = 'https://info.korea.ac.kr/info/board/news.do'
        URL_CAREER = 'https://info.korea.ac.kr/info/board/course.do'
        coi_list = {URL_GENERAL: 'coi_notice', URL_EVENT: 'coi_event', URL_CAREER: 'coi_career'}
        category = {'coi_notice': '정보대학 - 공지사항 ( 학부 )', 'coi_event': '정보대학 - 행사 및 소식', 'coi_career': '정보대학 - 진로정보'}
        session = requests.Session()
        for coi_key in coi_list.keys():
            await self.modern_board_posts_process(coi_key, category, coi_list[coi_key], session)

    async def modern_board_posts_process(self, url, category, cat, session):
        response = session.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        li_list = soup.select('#jwxe_main_content > div > div > div > div.t_list.test20200330 > ul > li')
        for li in li_list:
            span = li.find('span')  # find: 첫번쨰 occurence만 단일 객체로 반환
            span.i.extract()  # i 태그 제외
            date = str(span.text)
            date = date.replace('.', '-')

            a = li.find('a')
            title = a.text

            href = a.get('href')
            href_parsed = parse_qsl(href)
            link = (url + href)

            post_id = int(href_parsed[1][1])
            try:
                if post_id:
                    post = [post_id, title, link, cat, date]
                    if __debug__:
                        self.print_info(post)
                    post_id = await self.post_id_validate(category, post)
            except NameError:  # post_id를 가져오지 못 했을 때
                pass


    def get_login_info(self, list=False):
        with open('login.ini', 'r') as f:
            info_list = f.readlines()
            for info in info_list:  # 객체 전달 아님
                info_list[info_list.index(info)] = info.strip()
            if list:
                return info_list
            else:
                login_info = {'member_id': info_list[0], 'member_pw': info_list[1]}
                return login_info


    async def studyabroad(self):
        LOGIN_URL = 'https://studyabroad.korea.ac.kr/korea/login.do'
        URL_NOTICE = 'https://studyabroad.korea.ac.kr/studyabroad/community/notice.do'
        URL_PROGRAM = 'https://studyabroad.korea.ac.kr/studyabroad/community/infor.do'

        studyabroad_url = {URL_NOTICE: 'studyabroad_notice', URL_PROGRAM: 'studyabroad_program'}
        category = {'studyabroad_notice': '국제교류처 - 공지사항', 'studyabroad_program': '국제교류처 - 단기 프로그램 정보'}

        login_info = {'referer': '', 'site_id': 'studyabroad', }
        with requests.Session() as session:
            login_cred = self.get_login_info(list=False)
            login_info = {**login_info, **login_cred}
            login_request = session.post(LOGIN_URL, data=login_info)
            if __debug__:
                if login_request.status_code == 200:
                    print("로그인 성공")

            for url_key in studyabroad_url.keys():
                await self.modern_board_posts_process(url_key, category, studyabroad_url[url_key], session)


    async def portal(self):
        LOGIN_HOME = 'https://portal.korea.ac.kr/front/Intro.kpd'
        LOGIN_URL = 'https://portal.korea.ac.kr/common/Login.kpd'

        URL_BASE_FACE = 'http://portal.korea.ac.kr/front/PortletDetailList.kpd'
        URL_BASE = 'http://grw.korea.ac.kr'
        PATH_BASE = '/GroupWare/user/NoticeList.jsp'

        # boards = {'general' : 11, 'scholoar' :88, 'schedule' : 89, 'event' : 12}
        # 직접 접근할 때 게시판 ID

        boards = {'portal_general': 11, 'portal_scholar': 11, 'portal_schedule': 89, 'portal_event': 11}
        # 메인화면에서 게시판 ID

        category = {'portal_general': '포털 - 일반공지', 'portal_scholar': '포털 - 장학금공지', 'portal_schedule': '포털 - 학사일정',
                    'portal_event': '포털 - 교내외행사', 'portal_recent': '포털 - 최근게시물'}
        portletIds = {'portal_general': 'EM_NOTC_POS', 'portal_schedule': 'EM_SCHE_POS', 'portal_scholar': 'EM_NOTICE_8',
                    'portal_event': 'EM_NOTICE_3'}

        headers_portal_login = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://portal.korea.ac.kr/front/Intro.kpd',
            'Origin': 'https://portal.korea.ac.kr',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        with requests.Session() as session:
            response = session.get(LOGIN_HOME)
            soup = BeautifulSoup(response.content, 'html.parser')
            span = soup.find('span', {'class': 'input'})

            inputs = span.select('input')

            login_info = {'direct_div': '', 'pw_pass': '', 'browser': 'chrome'}
            login_cred_list = self.get_login_info(list=True)
            ID_KEY = inputs[2].get('name')
            PW_KEY = inputs[3].get('name')
            _csrf = inputs[4].get('value')
            dummy = inputs[5].get('value')

            login_cred = {ID_KEY: login_cred_list[0], PW_KEY: login_cred_list[1], '_csrf': _csrf, dummy: dummy}
            login_info = {**login_cred, **login_info}

            # 로그인
            if __debug__:
                if self.FIDDLER:
                    login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info, proxies=self.proxies,
                                                verify=self.verify)
                else:
                    login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info)
            else:
                login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info)

            for board_key in boards.keys():
                path = f'{PATH_BASE}?kind={str(boards[board_key])}'
                board_url = [URL_BASE_FACE, URL_BASE, path]
                await self.portal_posts_process(board_url, board_key, category, portletIds, session, headers_portal_login)


    async def portal_posts_process(self, url, cat, category, portletIds, session, headers):
        url_base_face = url[0]
        url_base = url[1]
        path = url[2]
        portletId = portletIds[cat]

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        data = {'portletId': portletId, 'queryYn': 'Y', 'url': url_base, 'path': path, 'compId': 'GROUPWARE',
                'menuCd': '', 'moreYn': 'Y'}

        if __debug__:
            if self.FIDDLER:
                response = session.post(url_base_face, headers=headers, data=data, proxies=self.proxies,
                                        verify=self.verify)
            else:
                response = session.post(url_base_face, headers=headers, data=data)
        else:
            response = session.post(url_base_face, headers=headers, data=data)
        soup = BeautifulSoup(response.content.decode('utf-8', 'replace'), "html.parser")

        li_list = soup.select('ul > li')
        for li in li_list:
            if "데이터가 없습니다" in li.text:
                break
            span = li.find('span', {'class': 'txt_right'})  # find: 첫번쨰 occurence만 단일 객체로 반환
            span.span.extract()
            date = str(span.text).strip()

            a = li.find('a')
            title = a.text.strip()

            href = a.get('href')
            href_parsed = href.split("'")[1]
            post_id = int(href_parsed)

            link = ('https://portal.korea.ac.kr')

            try:
                if post_id:
                    post = [post_id, title, link, cat, date]
                    if __debug__:
                        self.print_info(post)
                    post_id = await self.post_id_validate(category, post)
            except NameError:  # post_id를 가져오지 못 했을 때
                pass

    def print_info(self,post):
        print(f'''post_id: {post[0]}
    제목: {post[1]}
    링크: {post[2]}
    날짜: {post[4]}
    카테고리: {post[3]}''')

async def main():
    myBot = botAgent()
    await myBot.runBot()

if __name__ == '__main__':
    asyncio.run(main())
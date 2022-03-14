import telegram
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


def dorm_notice_init():
    dorm_list = {'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice2': 'dorm-total',
                 'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice': 'dorm-oldgik',
                 'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice1': 'dorm-newgik'}
    for dorm_key in dorm_list.keys():
        dorm_notice(dorm_key, dorm_list[dorm_key])


def get_post_id_from_javascript(href):
    post_id = int(href.split("'")[1])
    # if __debug__:
    #     print(f"post_id: {post_id}")
    return post_id


def dorm_notice(url, cat):
    response = requests.get(url)
    category = {'dorm-total': '안암학사 - 전체공지', 'dorm-oldgik': '안암학사 - 학생동공지', 'dorm-newgik': '안암학사 - 프런티어관공지'}

    soup = BeautifulSoup(response.content.decode('euc-kr', 'replace'), "html.parser")

    tr_list = soup.select(
        'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr')

    for tr in tr_list:  # 각 게시글 당
        td_list = tr.select('td')  # td 리스트 생성
        # if __debug__:
        #     print(f'td_list: {td_list}')
        for td in td_list:
            # 글 제목, id, 링크 가져오기
            a = td.find('a')
            try:
                href = a.get('href')
            except Exception:
                href = ''
            if 'javascript:viewBoard(document.BoardForm' in href:
                title = a.text
                post_id = get_post_id_from_javascript(href)
                link = f'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no={post_id}&s_type=1&s_text='

            # 게시일 가져오기
            if is_date(td.text):
                date = td.text

        try:
            if post_id:
                post = [post_id, title, link, cat, date]
                if __debug__:
                    print_info(post)
                post_id = post_id_validate(category, post)  # 이전 id 초기화
        except NameError:  # post_id를 가져오지 못 했을 때
            pass


def post_id_validate(category, post):
    cur.execute(f'''SELECT id FROM posts WHERE cat = '{post[3]}' AND id = {post[0]} ''')  # 테이블에서 데이터 선택하기
    # print(f"SELECT id FROM posts WHERE cat = '{post[3]}' AND id = {post[0]}")
    id = cur.fetchone()
    if id is None:  # 데이터베이스에 id가 없을 경우
        tel_bot(category[post[3]], post[1], post[2], post[4])
        cur.execute('''INSERT OR IGNORE INTO posts VALUES(?,?,?,?,?)''',
                    (post[0], post[1], post[2], post[3], post[4]))
    else:
        if __debug__:
            print(f"id {post[0]} 중복\n")
    return 0


def tel_bot(cat, title, link, date):
    title = title.replace('&', '&amp;')
    title = title.replace('<', '&lt;').replace('>','&gt;')
    text = f"""
    <b>{cat}</b>

<b>제목</b> {title}
<b>게시일</b> {date}"""

#     text = f"""
# *{cat}*
#
# *제목* {title}
# *게시일* {date}"""

    # text = text.replace("-", "\\-") #markdown parsing을 위해
    # print(text)

    is_portal = cat.find('포털')
    # if __debug__:
    #     print(is_portal)


    if is_portal != -1:
        text += f'\n\n<a href="{link}">포털 바로가기</a>'
        # text += f'\n\n[포털 바로가기]({link})'
    else:
        text += f'\n\n<a href="{link}">게시글 바로가기</a>'
        # text += f'\n\n[게시글 바로가기]({link})'


    # if __debug__:
    #     bot.sendMessage(chat_id=id, text=text, parse_mode="html")
    # id_channel = bot.sendMessage(chat_id='@korea_noti_test', text="I'm bot").chat_id  # @korea_noti_test 으로 메세지를 보냅니다.
    # print(id_channel)
    # with open('id_test.txt','w') as f:
    #     f.write(str(id_channel))
    # else:

    while True:
        try:
            bot.sendMessage(chat_id=id, text=text, parse_mode="html") #제목에 <> 등 들어가면 문제 발생함
            # bot.sendMessage(chat_id=id, text=text, parse_mode="MarkdownV2") #html보다도 고려해야 할 예외가 많음
            break
        except Exception as flood:
            print(f'Error: {flood}, waiting...')
            flood = str(flood).split(' ')[-2]
            sleep(float(flood))
            continue


def coi_notice():
    URL_GENERAL = 'https://info.korea.ac.kr/info/board/notice_under.do'
    URL_EVENT = 'https://info.korea.ac.kr/info/board/news.do'
    URL_CAREER = 'https://info.korea.ac.kr/info/board/course.do'
    coi_list = {URL_GENERAL: 'coi_notice', URL_EVENT: 'coi_event', URL_CAREER: 'coi_career'}
    category = {'coi_notice': '정보대학 - 공지사항 ( 학부 )', 'coi_event': '정보대학 - 행사 및 소식', 'coi_career': '정보대학 - 진로정보'}
    session = requests.Session()
    for coi_key in coi_list.keys():
        modern_board_posts_process(coi_key, category, coi_list[coi_key], session)


def modern_board_posts_process(url, category, cat, session):
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
                    print_info(post)
                post_id = post_id_validate(category, post)
        except NameError:  # post_id를 가져오지 못 했을 때
            pass


def get_login_info(list=False):
    with open('login.ini', 'r') as f:
        info_list = f.readlines()
        for info in info_list:  # 객체 전달 아님
            info_list[info_list.index(info)] = info.strip()
        if list:
            return info_list
        else:
            login_info = {'member_id': info_list[0], 'member_pw': info_list[1]}
            return login_info


def studyabroad():
    LOGIN_URL = 'https://studyabroad.korea.ac.kr/korea/login.do'
    URL_NOTICE = 'https://studyabroad.korea.ac.kr/studyabroad/community/notice.do'
    URL_PROGRAM = 'https://studyabroad.korea.ac.kr/studyabroad/community/infor.do'

    studyabroad_url = {URL_NOTICE: 'studyabroad_notice', URL_PROGRAM: 'studyabroad_program'}
    category = {'studyabroad_notice': '국제교류처 - 공지사항', 'studyabroad_program': '국제교류처 - 단기 프로그램 정보'}

    login_info = {'referer': '', 'site_id': 'studyabroad', }
    with requests.Session() as session:
        login_cred = get_login_info(list=False)
        login_info = {**login_info, **login_cred}
        login_request = session.post(LOGIN_URL, data=login_info)
        if __debug__:
            if login_request.status_code == 200:
                print("로그인 성공")

        for url_key in studyabroad_url.keys():
            modern_board_posts_process(url_key, category, studyabroad_url[url_key], session)


def portal():
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
        # 'User-Agent': ua.chrome,
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
        # if __debug__:
        #     print(f"id_key_slot: {span}")
        inputs = span.select('input')

        login_info = {'direct_div': '', 'pw_pass': '', 'browser': 'chrome'}
        login_cred_list = get_login_info(list=True)
        ID_KEY = inputs[2].get('name')
        PW_KEY = inputs[3].get('name')
        _csrf = inputs[4].get('value')
        dummy = inputs[5].get('value')

        login_cred = {ID_KEY: login_cred_list[0], PW_KEY: login_cred_list[1], '_csrf': _csrf, dummy: dummy}
        login_info = {**login_cred, **login_info}

        # 로그인
        if __debug__:
            if FIDDLER:
                login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info, proxies=proxies,
                                             verify=verify)
            else:
                login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info)
        else:
            login_request = session.post(LOGIN_URL, headers=headers_portal_login, data=login_info)

        for board_key in boards.keys():
            # cat = f'portal_{board_key}'
            # board_url = f'{URL_BASE}?kind={str(boards[board_key])}'
            path = f'{PATH_BASE}?kind={str(boards[board_key])}'
            board_url = [URL_BASE_FACE, URL_BASE, path]
            portal_posts_process(board_url, board_key, category, portletIds, session, headers_portal_login)
        # cat = 'portal_recent'
        # portal_posts_process(URL_BASE, category, session,headers_portal_login)


def portal_posts_process(url, cat, category, portletIds, session, headers):
    url_base_face = url[0]
    url_base = url[1]
    path = url[2]
    portletId = portletIds[cat]

    headers = {
        # 'Content-Type' : 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        # 'User-Agent': ua.chrome,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        # 'Cache-Control': 'max-age=0',
        # 'Referer': 'https://portal.korea.ac.kr/front/Intro.kpd',
        # 'Origin' : 'https://portal.korea.ac.kr',
        'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    # 바로 GET 꼬라박으면 죽음 (먼저 POST로 쿠키 겟또 해야 함)
    # if __debug__:
    #     print(session.cookies)

    data = {'portletId': portletId, 'queryYn': 'Y', 'url': url_base, 'path': path, 'compId': 'GROUPWARE',
            'menuCd': '', 'moreYn': 'Y'}

    if __debug__:
        if FIDDLER:
            response = session.post(url_base_face, headers=headers, data=data, proxies=proxies,
                                    verify=verify)
        else:
            response = session.post(url_base_face, headers=headers, data=data)
    else:
        response = session.post(url_base_face, headers=headers, data=data)
    soup = BeautifulSoup(response.content.decode('utf-8', 'replace'), "html.parser")

    li_list = soup.select('ul > li')
    for li in li_list:
        span = li.find('span', {'class': 'txt_right'})  # find: 첫번쨰 occurence만 단일 객체로 반환
        # span_inside_span = span.find('span')
        # print(span_inside_span)
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
                    print_info(post)
                post_id = post_id_validate(category, post)
        except NameError:  # post_id를 가져오지 못 했을 때
            pass

    # tr_list = soup.select('#Search > table > tbody > tr')
    # if __debug__:
    #     print(f'tr_list: {tr_list}')

    # for tr in tr_list:
    #     span = tr.find('span')  # find: 첫번쨰 occurence만 단일 객체로 반환
    #     span.i.extract()  # i 태그 제외
    #     date = str(span.text)
    #     date = date.replace('.', '-')
    #
    #     a = tr.find('a')
    #     title = a.text
    #
    #     href = a.get('href')
    #     href_parsed = parse_qsl(href)
    #     link = (url + href)
    #
    #     post_id = int(href_parsed[1][1])
    #     try:
    #         if post_id:
    #             post = [post_id, title, link, cat, date]
    #             if __debug__:
    #                 print_info(post)
    #             post_id = post_id_validate(category, post)
    #     except NameError:  # post_id를 가져오지 못 했을 때
    #         pass
    #


def print_info(post):
    print(f'''post_id: {post[0]}
제목: {post[1]}
링크: {post[2]}
날짜: {post[4]}
카테고리: {post[3]}''')


if __name__ == '__main__':
    if __debug__:
        FIDDLER = False
        if FIDDLER:
            proxies = {"http": "http://127.0.0.1:8888", "https": "http:127.0.0.1:8888"}
            verify = r"FiddlerRoot.pem"
    # ua = UserAgent()

    # DB 연결 및 테이블 생성
    if __debug__:
        conn = sqlite3.connect('notice_test.db')
    else:
        conn = sqlite3.connect('notice.db')
    # conn.row_factory = lambda cursor, row: row[0]  # fetchall시 튜플로 나오는 현상 방지
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE posts(id INT, title TEXT, link TEXT, cat TEXT, date TEXT, UNIQUE(id, cat))''')
    except:
        pass

    # 텔레그램 봇 초기화
    with open('token.ini', 'r') as f:
        my_token = f.read()  # 토큰을 설정해 줍니다.
    bot = telegram.Bot(token=my_token)  # 봇에 연결합니다.
    if __debug__:
        with open('id_test.txt', 'r') as f:
            id = int(f.read())
    else:
        with open('id.txt', 'r') as f:
            id = int(f.read())

    try:
        if __debug__:
            if not FIDDLER:
                dorm_notice_init()
                coi_notice()
                studyabroad()
            portal()
            link = 'https://telegram.org/blog/link-preview#:~:text=Once%20you%20paste%20a%20URL,now%20shown%20for%20most%20websites.'
            link2 = 'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no=40659&s_type=1&s_text='
            # tel_bot('테스트', '봇 테스트', link2, '2022-02-02')
            display_data = pd.read_sql_query("SELECT * FROM posts", conn)
            print(display_data)
        else:
            dorm_notice_init()
            coi_notice()
            studyabroad()
            portal()
    finally:
        conn.commit()
        conn.close()

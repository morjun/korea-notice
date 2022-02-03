import telegram
import requests
from bs4 import BeautifulSoup
import datetime
from dateutil.parser import parse
from urllib.parse import urlparse
from urllib.parse import parse_qsl
import sqlite3
import pandas as pd

if __debug__:
    conn = sqlite3.connect('notice_test.db')
else:
    conn = sqlite3.connect('notice.db')
conn.row_factory = lambda cursor, row: row[0]  # fetchall시 튜플로 나오는 현상 방지
cur = conn.cursor()

def is_date(string):
    format = "%Y-%m-%d"
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        # date = parse(string, fuzzy=fuzzy)
        datetime.datetime.strptime(string, format)
        # print(f"parsed date: {}")
        return True

    except ValueError:
        return False

def get_request(url):
    session = requests.session()
    response = session.get(url)
    # html = response.text
    return response

def dorm_notice_init():
    try:
        cur.execute('''CREATE TABLE posts(id INT, title TEXT, link TEXT, cat TEXT, date TEXT, UNIQUE(id, cat))''')
    except:
        pass

    dorm_list = {'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice2':'dorm-total', 'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice':'dorm-oldgik', 'https://dorm.korea.ac.kr:42305/src/board/list.php?code=notice1':'dorm-newgik'}
    for dorm_key in dorm_list.keys():
        dorm_notice(dorm_key,dorm_list[dorm_key])

def post_id_from_javascript(href):
    # post_id_str = href[-8:]
    # print(href.split("'"))
    # post_id = int(post_id_str.split("'")[0])
    post_id = int(href.split("'")[1])
    if __debug__:
        print(f"id: {post_id}")
    return post_id

def dorm_notice(url, cat):
    response = get_request(url)
    category = {'dorm-total' : '안암학사 - 전체공지', 'dorm-oldgik' : '안암학사 - 학생동공지', 'dorm-newgik' : '안암학사 - 프런티어관공지'}
    # html = response.text
    # print(html)

    soup = BeautifulSoup(response.content.decode('euc-kr', 'replace'), "html.parser")

    titles_candidates = soup.select(
        'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr > td > a'
    )
    dates_candidates = soup.select(
        'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr > td:nth-child(10)'
    )

    tr_list = soup.select(
        'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr'    )
    # print(titles_test) #항목 하나당 tr 하나

    # titles_can = soup.select('a')
    # titles = soup.find('a', {'href'})
    # print(titles)

    # titles = {}
    # temp_frame = pd.DataFrame(columns=['id','title','link','cat','date'])
    for tr in tr_list: #각 게시글 당
        td_list = tr.select('td') #td 리스트 생성
        if __debug__:
            print(f'td_list: {td_list}')
        for td in td_list:
            a = td.find('a')
            try:
                href = a.get('href')
            except Exception:
                href = ''
            if 'javascript:viewBoard(document.BoardForm' in href:
                title = a.text
                post_id = post_id_from_javascript(href)
                link = f'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no={post_id}&s_type=1&s_text='
            if is_date(td.text):
                date = td.text
                if __debug__:
                    print(f'날짜: {td.text}')

        try:
            if post_id:
                cur.execute(f'''SELECT id FROM posts WHERE cat = '{cat}' ''')  # 테이블에서 데이터 선택하기
                ids = cur.fetchall()
                if post_id not in ids:
                    tel_bot(category[cat],title,link,date)
                    cur.execute('''INSERT OR IGNORE INTO posts VALUES(?,?,?,?,?)''',
                                (post_id, title, link, cat, date))
                else:
                    if __debug__:
                        print(f"id {post_id} 중복")
            post_id = 0 #이전 id 초기화
        except NameError: #post_id를 가져오지 못했을 때
            pass



def tel_bot(cat, title, link, date):
    text = f"""
    <b>{cat}</b>
    
<b>제목</b> {title}
<b>게시일</b> {date}

<a href="{link}">게시글 바로가기</a>
    """
    # if __debug__:
    #     bot.sendMessage(chat_id=id, text=text, parse_mode="html")
        # id_channel = bot.sendMessage(chat_id='@korea_noti_test', text="I'm bot").chat_id  # @korea_noti_test 으로 메세지를 보냅니다.
        # print(id_channel)
        # with open('id_test.txt','w') as f:
        #     f.write(str(id_channel))
    # else:
    bot.sendMessage(chat_id=id, text=text, parse_mode="html")


def coi_notice():
    URL_GENERAL = 'https://info.korea.ac.kr/info/board/notice_under.do'
    URL_EVENT ='https://info.korea.ac.kr/info/board/news.do'
    URL_CAREER = 'https://info.korea.ac.kr/info/board/course.do'

    response = get_request(URL_GENERAL)
    soup = BeautifulSoup(response.content, "html.parser")
    li_list = soup.select('#jwxe_main_content > div > div > div > div.t_list.test20200330 > ul > li')
    if __debug__:
        print(f"li_list: {li_list}")


if __name__ == '__main__':
    with open('token.ini', 'r') as f:
        my_token = f.read() # 토큰을 설정해 줍니다.
    bot = telegram.Bot(token=my_token)  # 봇에 연결합니다.

    if __debug__:
        with open('id_test.txt', 'r') as f:
            id = int(f.read())
    else:
        with open('id.txt', 'r') as f:
            id = int(f.read())

    try:
        dorm_notice_init()
        if __debug__:
            coi_notice()
            link = 'https://telegram.org/blog/link-preview#:~:text=Once%20you%20paste%20a%20URL,now%20shown%20for%20most%20websites.'
            link2 = 'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no=40659&s_type=1&s_text='
            tel_bot('안암학사 - 전체공지', '중복 공지 테스트', link2, '2022-02-02')
            # display_data = pd.read_sql_query("SELECT * FROM dorm", conn)
            # print(display_data)
    finally:
        conn.commit()
        conn.close()

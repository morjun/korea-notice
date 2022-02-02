import telegram
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from urllib.parse import urlparse
from urllib.parse import parse_qsl
import sqlite3
import pandas as pd

conn = sqlite3.connect('notice.db')
conn.row_factory = lambda cursor, row: row[0]  # fetchall시 튜플로 나오는 현상 방지
cur = conn.cursor()

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
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
        cur.execute('''CREATE TABLE dorm(id INT, title TEXT, link TEXT, cat TEXT, date TEXT, UNIQUE(id, cat))''')
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
        print(post_id)
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

    # titles_test = soup.select(
    #     'body > table > tr > td:nth-child(2) > table > tr:nth-child(4) > td:nth-child(2) > table > tr:nth-child(4) > td.ForPrint > table > form > tr > td > table > tr'    )
    # print(titles_test)

    # titles_can = soup.select('a')
    # titles = soup.find('a', {'href'})
    # print(titles)

    # titles = {}
    # temp_frame = pd.DataFrame(columns=['id','title','link','cat','date'])

    date_list = []
    info_list = []
    for date in dates_candidates:
        date_text = date.text
        if is_date(date_text, fuzzy=False):
            # temp_frame['date'] += date_text
            date_list.append(date_text)
            if __debug__:
                print(date_text)

    for title in titles_candidates:
        href = title.get('href')
        if ('javascript:viewBoard(document.BoardForm' in href):
            # post_id = int(href[-8:-3])
            post_id = post_id_from_javascript(href)
            link = f'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no={post_id}&s_type=1&s_text='
            # temp_frame['link'] += link
            # temp_frame['title'] += title.text
            # temp_frame['cat'] += 'dorm_total'
            info_list.append([post_id, title.text, link, cat])
            # if __debug__:
            #     parsed = urlparse(link)
            #     print(parse_qsl(parsed.query)[2][1])

    length = len(info_list)
    if length == len(date_list):

        for i in range(length):
            cur.execute(f'''SELECT id FROM dorm WHERE cat = '{info_list[i][3]}' ''')  # 테이블에서 데이터 선택하기
            ids = cur.fetchall()
            if info_list[i][0] not in ids:
                tel_bot(category[cat],info_list[i][1],info_list[i][2],date_list[i])
                cur.execute('''INSERT OR IGNORE INTO dorm VALUES(?,?,?,?,?)''',
                            (info_list[i][0], info_list[i][1], info_list[i][2], info_list[i][3], date_list[i]))
            else:
                if __debug__:
                    print("중복")
            # print(title.text)
            # print(
            #     f'https://dorm.korea.ac.kr:42305/src/board/view.php?page=1&code=notice2&mode=&no={titles[title]}&s_type=1&s_text=')


def tel_bot(cat, title, link, date):
    text = f"""
    <b>{cat}</b>
    
<b>제목</b> {title}
<b>게시일</b> {date}

<a href="{link}">게시글 바로가기</a>
    """
    bot.sendMessage(chat_id=id, text=text, parse_mode="html")

    # id_channel = bot.sendMessage(chat_id='@korea_notice', text="I'm bot").chat_id  # @korea_notice 으로 메세지를 보냅니다.
    # print(id_channel)
    # with open('id.txt','w') as f:
    #     f.write(str(id_channel))

def coi_notice():
    URL_GENERAL = 'https://info.korea.ac.kr/info/board/notice_under.do'
    URL_EVENT ='https://info.korea.ac.kr/info/board/news.do'
    URL_CAREER = 'https://info.korea.ac.kr/info/board/course.do'

    response = get_request(URL_GENERAL)
    soup = BeautifulSoup(response.content, "html.parser")
    titles = soup.select('#jwxe_main_content > div > div > div > div.t_list.test20200330 > ul > li')
    if __debug__:
        print(titles)


if __name__ == '__main__':
    with open('token.ini', 'r') as f:
        my_token = f.read() # 토큰을 설정해 줍니다.
    bot = telegram.Bot(token=my_token)  # 봇에 연결합니다.

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

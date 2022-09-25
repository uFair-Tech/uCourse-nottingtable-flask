import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
#from lxml import etree
#实现无可视化界面
from selenium.webdriver.chrome.options import Options
#实现规避检测
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By

from nottingtable import db
from nottingtable.crawler.ics_helper import get_cal
from nottingtable.crawler.ics_helper import add_whole_course
from nottingtable.crawler.courses import add_course
from nottingtable.crawler.modules import get_module_activity
from nottingtable.crawler.models import Course


def validate_student_id(student_id, is_year1=False):
    """
    Get and verify student id
    :param student_id:
    :param is_year1: whether the student is year 1 student
    :return: a boolean
    """
    if not is_year1:
        if not re.match(r'\d{8}', student_id):
            return False
        else:
            return True
    else:
        if not re.match(r'Year 1-.*-\d{2}.*', student_id):
            return False
        else:
            return True


def validate_hex_id(hex_id):
    """
    Get and verify hex id
    :param hex_id:
    :return: a boolean
    """
    if re.match(r'([0-9A-F]{32}).*', hex_id):
        return True
    else:
        return False


def get_time_periods():
    """
    Generate time periods list from 8:00 to 22:00
    :return: time periods list
    """
    periods = []
    for h in range(8, 22):
        for m in range(2):
            periods.append(str(h) + ':' + ('00' if m == 0 else '30'))
    periods.append('22:00')
    return periods


def get_individual_timetable(url,student_id, is_year1=False):
    """
    Get individual timetable
    :param url: base url of timetabling server
    :param student_id: student id or group id for year 1
    :param is_year1: whether the student is year 1 student
    :return: timetable dict for the student
    """


    # 实现无可视化界面的操作
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.page_load_strategy = 'eager'

    # 实现规避检测
    option = ChromeOptions()
    option.add_experimental_option('excludeSwitches', ['enable-automation'])




    # 实现让selenium规避被检测到的风险
    driver = webdriver.Chrome(executable_path='/Users/mayuhao/uCourse-nottingtable-flask/venv/lib/python3.10/site-packages/chromedriver',chrome_options=chrome_options,options=option)



    driver.get("https://unnc-sws-ad.scientia.com.cn/TCS/view")
    input = driver.find_element(By.ID,'i0116')
    #input email
    input.send_keys('UNNC_email')
    button1 = driver.find_element(By.ID,'idSIButton9')
    button1.click()
    sleep(4)
    pw = driver.find_element(By.ID,'passwordInput')
    #inuput password
    pw.send_keys('Password')
    button2 = driver.find_element(By.ID,'submitButton')
    button2.click()
    button3 = driver.find_element(By.ID,'idSIButton9')
    button3.click()
    cookie = driver.get_cookies()[0]
    #print(cookie['value'])

    driver.quit()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://unnc-sws-ad.scientia.com.cn',
        'Connection': 'keep-alive',
        'Referer': 'https://unnc-sws-ad.scientia.com.cn/',
        'Cookie':'.AspNetCore.AzureADCookie='+cookie['value'],
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }

    if is_year1:
        student_id_1 = student_id.split('-')[1]
        student_id_2 = student_id.split('-')[2]
        student_id = student_id_1 + student_id_2

    data = {
        'identifier': student_id,
        'style': 'Individual',
        'weeks': '2-3;5-14',
        'days': '1-5',
        'periods': '1-24',
    }

    res = requests.post('https://unnc-sws-ad.scientia.com.cn/TCS/view', headers=headers,
                             data=data)

    if res.status_code != 200:
        raise NameError('Student ID Not Found.')


    soup = BeautifulSoup(res.text, 'html.parser')
    #print(soup)

    name = soup.select('table table tr')[1].get_text()
    if not is_year1:
        name = name.split('/')
        try:
            name = name[-3] + ' ' + name[-2]
        except IndexError:
            pass
    print(name)
    timetable = soup.find(border='1')
    periods = get_time_periods()
    timetable_list = []
    is_time_period = True
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    current_weekday = ''
    for tr in timetable('tr'):
        if is_time_period:
            is_time_period = False
            continue
        else:
            time_period_index = 0
            for td in tr.children:
                if td.name != 'td':
                    continue
                if not td.has_attr('rowspan'):
                    time_period_index = time_period_index + 1
                    continue
                if td.get_text() in weekdays:
                    current_weekday = td.get_text()
                    continue
                assert td['rowspan'] == '1'
                course_info = td.find_all('table')
                activity_id = course_info[0].tr.td.get_text().replace('  ', ' ')
                course_id = course_info[1].tr.td.get_text()
                third_row_info = course_info[2].tr.find_all('td')
                room = third_row_info[0].get_text()
                staff = third_row_info[1].get_text()
                weeks = third_row_info[2].get_text()
                start_time = periods[time_period_index]
                time_period_index = time_period_index + int(td['colspan'])
                end_time = periods[time_period_index]

                module = Course.query.filter_by(activity=activity_id).first()
                if not module:
                    # For a few newly added course, use hot update via Courses API
                    # But re-craw courses table is more recommended
                    new_course = get_module_activity(re.match(r'(https?://.*?/)', url).group(1), course_id, activity_id)
                    new_course_record = add_course(new_course)
                    db.session.commit()
                    module = new_course_record
                module = module.module

                timetable_list.append({
                    'Activity': activity_id,
                    'Course': course_id,
                    'Module': module,
                    'Room': room,
                    'Staff': staff,
                    'Start': start_time,
                    'End': end_time,
                    'Weeks': weeks,
                    'Day': current_weekday
                })
    return timetable_list, name


def generate_ics(record, start_week_monday):
    """
    Pair course activity and course info
    :param record: timetable list from individual web page
    :param start_week_monday: arrow object
    :return: ics_file
    """
    ics_file = get_cal()
    for course in record.timetable:
        # course is from individual webpage
        # course_info is from course page cached in the database
        course_info = Course.query.filter_by(activity=course['Activity']).first()
        course['Module'] = course_info.module
        course['Name of Type'] = course_info.type
        add_whole_course(course, ics_file, start_week_monday, record.timestamp)
    return ics_file.to_ical().decode('utf-8')

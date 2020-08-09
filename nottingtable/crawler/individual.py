import re
import requests
from hashlib import md5
from bs4 import BeautifulSoup
from icalendar import Calendar, Event, Alarm
import arrow

from nottingtable import db
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
        if not re.search(r'[ABC]-\d{2}', student_id):
            return False
        else:
            return True


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


def weeks_generator(week_str):
    """
    Generator function for (a-b, c-d, e) format
    :param week_str: week_str from individual page
    :return: week iterator
    """
    week_periods = week_str.split(', ')
    for week_period in week_periods:
        dash_index = week_period.find('-')
        if dash_index == -1:
            week_num = int(week_period)
            yield week_num
        else:
            week_start_num = int(week_period[:dash_index])
            week_end_num = int(week_period[dash_index + 1:])
            current_week = week_start_num
            while current_week <= week_end_num:
                yield current_week
                current_week = current_week + 1


def get_individual_timetable(url, student_id, is_year1=False):
    """
    Get individual timetable
    :param url: base url of timetabling server
    :param student_id: student id or group id for year 1
    :param is_year1: whether the student is year 1 student
    :return: timetable dict for the student
    """
    if is_year1:
        url = url + 'reporting/Individual;Student+Sets;name;{}?template=Student+Set+Individual' \
                    '&weeks=1-52&days=1-7&periods=1-32'.format(student_id)
    else:
        url = url + 'reporting/individual;Student+Sets;id;{}?template=Student+Set+Individual' \
                    '&weeks=1-52&days=1-7&periods=1-32'.format(student_id)

    res = requests.get(url)
    if res.status_code != 200:
        raise NameError('Student ID Not Found.')
    soup = BeautifulSoup(res.text, 'lxml')
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
                activity_id = course_info[0].tr.td.font.get_text().replace('  ', ' ')
                course_id = course_info[1].tr.td.font.get_text()
                third_row_info = course_info[2].tr.find_all('td')
                room = third_row_info[0].font.get_text()
                staff = third_row_info[1].font.get_text()
                weeks = third_row_info[2].font.get_text()
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
    return timetable_list


def generate_ics(record, start_week_monday):
    """
    Pair course activity and course info
    :param record: timetable list from individual web page
    :param start_week_monday: arrow object
    :return: ics_file
    """
    weekday_to_day = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    ics_file = Calendar()
    ics_file.add('version', '2.0')
    ics_file.add('prodid', 'Nottingtable')
    for course in record.timetable:
        # course is from individual webpage
        # course_info is from course page cached in the database
        week_iterator = weeks_generator(course['Weeks'])
        course_info = Course.query.filter_by(activity=course['Activity']).first()
        start_time = arrow.get(course['Start'], 'H:mm')
        end_time = arrow.get(course['End'], 'H:mm')
        for week in week_iterator:
            course_date = start_week_monday.replace(tzinfo='Asia/Shanghai') \
                .shift(weeks=+(week - 1), days=+weekday_to_day[course['Day']])
            e = Event()
            e.add('uid', md5((course['Activity']+course_date.format()).encode('utf-8')).hexdigest())
            e.add('summary', course_info.module + ' - ' + course_info.activity)
            e.add('dtstart', course_date.shift(hours=start_time.hour, minutes=start_time.minute).to('utc').datetime)
            e.add('dtend', course_date.shift(hours=end_time.hour, minutes=end_time.minute).to('utc').datetime)
            e.add('dtstamp', record.timestamp)
            e.add('location', course['Room'])
            e.add('description', course_info.type + '\r\n' + 'Staff: ' + course['Staff'])
            a = Alarm()
            a['trigger'] = '-PT15M'
            a['action'] = 'DISPLAY'
            a['description'] = course_info.module
            e.add_component(a)
            ics_file.add_component(e)
    return ics_file.to_ical().decode('utf-8')

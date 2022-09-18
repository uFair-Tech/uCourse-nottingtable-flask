import re
import requests
from bs4 import BeautifulSoup
#from lxml import etree

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
    """
    url = url + 'reporting/individual;Student+Sets;{};{}?template=Student+Set+Individual' \
                '&weeks=1-52&days=1-7&periods=1-32'.format("name" if is_year1 else "id", student_id)
    res = requests.get(url)
    """

    cookies = {
        '.AspNetCore.AzureADCookie': 'CfDJ8DCrHEQIyM5PrbMrShIGWc6VSGk3FF1V4CtL8YB38ZruOOl05oA8pSSPuDUcS7JfmdnQ_VnFos6VClIM_fDhOQW6akJhrNlQW5INvyOffHP4K3oputrrYwwHLL9HBmoW4iE_RCc7P9k9OwL3E9B-KTt9BaRpB4XBGi2CUdR-dUkY3-n60jX3UjLoxUjmrc7-Cb_wllsPnqFLohCVE2UUWwSrJqoQMR0lTeawI9a9_MngvVR08mCmy0ghEN23Slq_VwYuGiB8rlAMXYUB-y4TJpZGXitb4KKZii0BHfvyMQUpwOVHo4wQLmZpvvN4dxHZPdB0_UnTiI9TVXQRzmtp3prdHiETnUxqphtP11ggFRCdjn4NzsnnPFXwrK-eJqRpKDXiMJzANXQH33v733tNAnnJYnjkCdWwxdAJKS3CPyJwquvqYVlNteYujvm-1lkFCqxiCZ2jTldFu-ZffchR3p3NnrO64B_1mOjL9uZl9w3-4glGe5eYab9iJFl7-kmX0ZHrhXojvKWZjI-lNJhqoNfeNqJtLdlejdnyoQtuEgrgANLdNqol4vyyfSvbTCQUOEhr-DlGOb6Byi4-ImPF_7XcavD5uj-7jyLCsCpo2OK5QgSxhBBqBlaysk_4gW-9XVY6DG4C64de1mPndnUbTeQYs6t1cgFJ2c2-xd7bPF_s6wHiaRC72FWdsoCN4v_5FSNIy03XfJ3_fLOZBQLCKEAOnW-x6KqIMxVFRHb8AM5YM1uW-vF60xTNrFFwd3R0HhFpSp2hTJJvOqDT-NJo0IcXEFUSjtF5wwz6DKaNa01Gs2K7kT8CQSkv49i0a1poKCAxe3Qbo333U2ySsdyv3tn37C_c-8b3Vp3XWnTVbRvrhIq4fZW5a4bYtFepzunb5pl2wCPvpgyCFqiWAI27zs8OQ5rK2apB7rJqXlyCZszRGWMvgRTquuypouh0gGXT4k-0G0_RGGQ3kpgWTvTlsYTGTZpSO8wOkeAFGOJbYwwDGVrQEQIdaQmMPz3paVZCchRmiOvy5VDhSUQ5qmf7VdXZL7eii1oTdYMpYIR9VS648arOml9KtKlG7blKgXf5Z75l_PZUc5xUcmzPER2SB1zdtke_uSHVhzrqfbpEG2GZMkJNEH-UJi2Dj2pfZX1byLApZupSL-3_RmpJPn4WXRV2IM0XwbrwkfMoRx48yhbYppGK_oLQpqOss_u5UOPc80IFeRnKylingS_UVAFTNBm-zsb_ubHKTAUSp0eMJ6r7lPWdwGTkhIEaBGFYzARSiZ-lzvhx3nhGp-2-56thmb3J1IdocS95mInzBQqJyTadmn6IHkvArL99pjQf2U1GpnH_1QdrM1NAd_HMWdBKt1mQbFOQtf1yXPYvVGWj57OOcYwajPcltbK72avYstX31hvf5KiLxcf0t13jiBgN9cgTf-HiVcnQef-XvcZ9-ex97HWbtuPaPurKrm2-Uot5gajq8leGcWEXGlTGc-39Pgf-s70XcpoKl-xjwiA2L_piIuicw7HJqCB07Frazf_nbPibkOw_T3G1049e9c-brG0riQVyACYs0Oi2INTIc9VYj3UWKIoQMnNfcJCQBxT2yMx2Lo1Itr9O5Yt96wXP5DUNXgELYS4TtNq77OLDBLzCBQO68loW1yx-LvXdD0-LNmCvphHruMn4OCW9RSQ3vE9gpe1QG6P1RQSKrJrXW5kb8lewlC2SopK_Z2Xi2lA0wrX-pXgfF-AHjuGuLhLe-Fmsn9qOfpMjqlH9QjesPHYZXGDpMV3Sk2tQVa0gDNeVDQFVuPZVBluvfMCBy21b_HZZTGwy9S838EeeCHXxumUCut60DgX6H04nvf4GdPJnbqoKIibwMAPi1IpBoMKREb8PN5Z9_Pk4WQrysv4xWQJ0DoE2np37J6sn9G8D1ff6VlcoScnRqahfy9XWoX3j7LxeXOc4f121ZO5LC2sGlandTTwwb6HA5pr5w0_CeBW2yuBRA1E4CAjvAqywx0ILHTxCgXg0-JEosmXjCb4H1k3eKv62Ty9pVY2EfgLU1qtMcEyCVOzrNC7bVc9Mw2vKjSEaPpHXT7J7arhvIz8E4CpbcwYD8GX7MqC5-7w-LbQ3IQ0VcEkkHghU8iMOEnOO2y61QHTmE_BFQM716Toa7iAVSMf23L-eZba9NDB8c_0KQd5YTg4EGA_1sowQ5yNX4lhC4oVindV6EizPb9fAW_uWqzjLd9Xe-XPn4aWD1KiDOZHqdJfiwokOJsBXRAfDFPDw68bzAt0oolhxuJgewlv0pzi8whoqVpwF5Cuas6d9awvq-6opTHIN4LGxfJjDB-whulsOW-yNIikwlcCOobti5PzkLgwEXUQ2kxjkA69oynJG4M0LOGBWkU12BRXzSehUG8MFcOXyTFUQPoxLtD2nkG_-iU4XzaTG6JeIzZ6g0cv5IdHqeJKEkhow4IcsI2gk0R_SE4_U0DD58bYUH5ReUfNKb6QLWK2akTFPhUOgxKqhh1DhBwXNX9zeWdaf3PPhJyHmp2XddMlHTbaT0kPxRwaftRofV9dmNN6-chi9sRt_geyRM9AhZqhF7ptdGvMJO84jUm3I549dnuic7c5ScknM2tZ8J0RvHWA9BYaKWeRsMLWEM4awUAXMDMIB1eR7sN87Dxa4jQLMjdoCbMSMY2P4VvVAb9Mo1HfCtkc_qOqWVXzy592g8GYrcrajn_OYFrYdMkcolwH5kTbLIWyA522N7Ovmv701Aj0nZy9ScuF4ZAIeFTuXrQDk8wDuSgSH8QjlljTUQ3g4QabRWnUFFrSoMf_o1d2q3KdIK9YQuflVLNcdlCK5PHtiaCgEvm_R7YwcMgrV5DjVPckSwFTi9rr-GWeykDki5dMXU1M4lIQ6rWa2lE5aTYNlJmH4eDM',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://unnc-sws-ad.scientia.com.cn',
        'Connection': 'keep-alive',
        'Referer': 'https://unnc-sws-ad.scientia.com.cn/',
        # 'Cookie': '.AspNetCore.AzureADCookie=CfDJ8DCrHEQIyM5PrbMrShIGWc7F05kp0aJ7RK_UDrE6ZlldbLtE2ipBJFOwmzXex4LmpqQYPQLBsj6g2Ps93QXpGYmjeDG9HKZhsCGsGwy_cGByIm9G8ZqHcYRTmpoVVzMFSIXkoi2H7sxZ7Xl7uXW85UNW9Hm2d4iEbWe5aWgyADZv8GvUiaE9vX_OgdPrWc25l--H6yKjnbhFg60pwR6Pys-aCEEF9NNDWj3rGr9_V2BwZtTIpc4S0k8ccMJTNdCXPfhHLJjBeaCirocXiB2dVbfw7TjmBmSgTZkIwrXPwEagBDsSS5ZHXAqzbHeGT5md8PvIwHFh4S4bIwg_YybVZ-QgUh_XMwUTIA6cc-F5YLnYATcnOvmokXjBJdrM8WdndaFUOFFr5wJvP85DL6flL31xyp6ojZFn6c3cdONi60vDSDlAgC5ivm-CdlKWqCbC4YexT9xQTg-tZf5RJ2TL5QoxkOn8h3sEtk-eEmdMV3f-LDCkn6bnWRpe3VeqBq7qnMT4mzEhOVOeerfYyDdogFwckSfHtPM3RsX_tb0XNF7vhiHoC7EM-mWDQ-iKhuwAxWKCurV1keRH4-wg9CI42-KV08FRu3hUELCfz3icy3mW0YGdsDfvZm-I8l4RCBU_Br6GG8P1T7kj9-D0rtg82UITUlhhCst_6mkZUBjMww4bitJ4GXMSNiSggQe8_tLndxaM1tWN-WjcQIQN3fOFZxcIsnV0_bOLwhzx-kyawrdNqZTuidYpSWMwO7mK3jyMUk1Ri62KDWIDOhcLA6ra7Dp6jpNFI-9YomgGi8YTUwWUQjmjSkEqbLPvqCDYNGDslp8Oq89bbQc1LZ4hDOhXlH4mWOeMkCajDbCjJ_rvm-GHnPVeXjHUfPEnfxzvfLFIJXIbjUn2xdqjwCIs583hSEORVPxsMHAvV0gc4ZZKoE3dWZilF8-cTq_i3hguZ18iyFXdu3MQ5m2_Icuj8U7zT6Yba31GJj4HN_zXm6rwlZNxvgEZO7qrh3b2gdx7QSprXoLku5EhqqybaPgnSn864ATXYKO5o63BXCUvfp1-7HM7CdvMWjkQrBIluGkoikGaeH5Hcy81q4Jn_efmUC-XJVffuPg3xb2_Vh8RuQWcRqW3qW9srJx1Z4TKdl7waEftJI73yvnx9j-PCgPZNb_5HXUPo7-I5FonQkWAvKKQ-4J3Rq9STubuaGZML4hEtlX7WLmHTc5Ikg_ZLJteXKz9eXKIy9R956G4hJOsoZMinxGwCXpPrp--6hE_oIoqvWLPnfUd_Na5HX8bW2SQIiuaKgqwZoAFqfQ_fb8B_hZtEh21BE-p3oVmouSvxI1S_AQtM2MuszkHCA460qtDCjH_VgqVC9vBUjXZlMLwbflfqyEzE_H3AvuEThO8NTG9KyfXOiqUqHSWjHY-XH6FFWfxuEPzOvMyrsRhrm8b1ZfY5qKnetpiYaphw4nDufjGuDzzjWHGG8citYsw_4-CngZGPtM3emrpHRnEoyjGPV_8QV0rBUo0ncOaEPtLTy3j1OFJIqDj238QSfYi1OGMhdzlAK6onMMGmhgTCGvHYZqpps5SyrkqyMp5D-4w9O99yB8qVsKnzry4_R6WU0IkRrKvouWGvDLIAmcKIeyVUdGx6tcMCUfQoXLYtZX3Y9KxYfqTfc28OwWA_oeLhtoZT_rOhL3LBKnimGNEs0nDfFrMkffqqF9zrnDCA3nhKsoc59gRU6-fnXW1KbJimJXrf44BzYsfdHCY4qvHCBoCptzCF089lVM0o8PN7Quw_HHEuz9wPJQMgxnm35iaVMIDqr5BgWzKFzrBMkHpMBH6fSp-jE6l0nDe-6uZSXKOxqR_iQCKng8WA8oYd_K9V1P0MDo4L7fx1SJxqfg47_-UpkhkKctL11PMGhbZf9sBi_BmNkf3eLy3T4a4GCqydWOo6o-s7dJq24C6QKi5jtMdnRe_rqc8bVMQpZj1yjuYmX7BWm_8zlzyqNSubAf6YFOrznc4xCFxlUNbu8CS6BBoBwqnsd_hsjgcPc_TnnmNiWo4Wg7RxTI63Q47p5rpjQvXIiLZOZYM6PnFjw8tk7qXSwUQpAkF2OfEqyk_X4WTIPWnHidXee6DGH3oJ7vce68Rc5cLhXnvRYH0lL0-Nz9OykxxKfjBoAG66JINYNnoH5QbZBgeWyCVaiQrULBr2fWwZVzRer8rFdgezPem4kswYoQrO1bGMQ4oxSBK-yUD0QZqi3wyLX3TAgrl5ua-W7NojF12kfQONkJxa0BJu2ZDAhVU0-xRXJeL3Tert0Y_g7eiQKT9XB5Xus0H4IgP6I-F-vj4i5-WFEJNrx49vjLhoU1CskHBWNaT3YjRgovu3CiOonULQ5h3ewinP7n06Il32zjquNit5bHwwMhqqGdK3wokDnmwbPxttIayFJiTXp7XNegWqk8YxeE6GlgaHMaMVMcL5lfHo3D25TQ7_PN6_KpW5Y6V7bzO0Hyimd6ZHw5lHir1CZRDbf3C4omzp2H20jH9yOsMa5eG1_qEb3WummzcxguZWqSyTUA1D-4M-E4IdBomktgVyVYcTXJIzzuvQTP69qCmP5F5uC6LAhl3sxnivLb33Tm8ZFiQPoMrzxLNW35MRbpjzRZP6fdY0oGMp85uiXvoM5NG-dqkisvyoxxN5xeOMx-SvmGpkL3rbTS5w2Q8rpDayExtByjQqO86roXC6HwiANre_XwQo3bYce2mICYtfehj45Xojzn92WIfvfVPbJpba-j1BE9BxDjimKYS1qVx_fOJ9tvccEo0QquT42KtuI1U38m5J7rzM3GVt3Xwy5Eb0ZMMJC8MOQWxphz1ArLkYtIzsZpVr1W7RI3RV5QraM_Z6GQGssBgdJ75yXeR6jmdXYMfT8MdL8JOR5M4jNo',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }

    data = {
        'identifier': student_id,
        'style': 'Individual',
        'weeks': '2-3;5-14',
        'days': '1-5',
        'periods': '1-24',
    }

    res = requests.post('https://unnc-sws-ad.scientia.com.cn/TCS/view', cookies=cookies, headers=headers,
                             data=data)
    if res.status_code != 200:
        raise NameError('Student ID Not Found.')
    soup = BeautifulSoup(res.text, 'html.parser')
    print(soup)
    """
    tree = etree.HTML(res.text)
    print(tree)
    name = tree.xpath('/html/body/div/main/table[1]/tbody/tr[2]/td/table/tbody/tr/td[2]/text()')[0]
    """
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

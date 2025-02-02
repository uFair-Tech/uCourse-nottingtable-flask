import arrow
import requests

from flask import Blueprint
from flask import current_app
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for

from nottingtable.api.views import add_or_update
from nottingtable.api.views import _get_record
from nottingtable.api.views import filter_semester, get_current_semester
from nottingtable.crawler.individual import get_individual_timetable
from nottingtable.crawler.plans import get_plan_textspreadsheet
from nottingtable.crawler.staff import get_staff_timetable
from nottingtable.crawler.models import Y1Group
from nottingtable.crawler.models import MasterPlan

bp = Blueprint('front', __name__, template_folder='templates')


@bp.route('/', methods=('GET',))
def index():
    start_date = current_app.config['FIRST_MONDAY']
    end_date = start_date.shift(weeks=52, days=-1)
    return render_template('index.html', start_date=start_date.date(), end_date=end_date.date())


@bp.route('/year-24', methods=('GET',))
def show_year_24():
    return render_template('year-24.html')


@bp.route('/year-1', methods=('GET',))
def show_year_1():
    """
    Render page for year1 selection page
    :return: rendered page with selection list
    """

    group_list = Y1Group.query.all()
    return render_template('year-1.html', group_list=group_list)


@bp.route('/plan', methods=('GET',))
def show_plan():
    """
    Render page for master students
    :return: rendered page with selection list
    """

    plan_list = MasterPlan.query.all()
    return render_template('plan.html', plan_list=plan_list)


@bp.route('/staff', methods=('GET',))
def show_staff():
    """
    Render page for staff
    :return: rendered page with staff input box
    """
    return render_template('staff.html')


@bp.route('/about', methods=('GET',))
def show_about():
    """
    Render about page
    :return rendered about page
    """
    return render_template('about.html')


@bp.route('/qna', methods=('GET',))
def show_qna():
    """
    Render Q&A page
    :return: rendered Q&A page
    """
    return render_template('qna.html', official_link=current_app.config['BASE_URL'])


@bp.route('/usage', methods=('GET',))
def show_usage():
    """
    Render usage page
    :return: rendered usage page
    """
    return render_template('usage.html')


@bp.route('/check', methods=('POST', 'GET'))
def check_cal():
    """Show the list of all calendar events"""

    def get_link():
        """Generate download links"""
        if data['type'] == 'year-1':
            return url_for('api.get_individual_data', format_type='ical', group=student_id, _external=True)
        elif data['type'] == 'year-24':
            return url_for('api.get_individual_data', format_type='ical', id=student_id, _external=True)
        elif data['type'] == 'plan':
            return url_for('api.get_plan_data', format_type='ical', plan=student_id, _external=True)
        elif data['type'] == 'name':
            return url_for('api.get_staff_data', format_type='ical', name=student_id, _external=True)

    if request.method == 'GET':
        return redirect(url_for('index'))

    # Defense
    types = ['year-1', 'year-24', 'plan', 'name']
    data = request.form
    if not data.get('type') in types:
        return render_template('check.html', timetable=None)

    force_refresh = data.get('force-refresh')
    student_id = data.get('hex') or data.get('group') or data.get('plan') or data.get('name')
    record, force_refresh = _get_record(student_id, force_refresh)
    fields = ['Activity', 'Module', 'Day', 'Staff', 'Start', 'End', 'Weeks']

    if force_refresh:
        url = current_app.config['BASE_URL']
        if data['type'] == 'year-1':
            try:
                # student_hex_id = get_hex_id(student_id)
                timetable, name = get_individual_timetable(url, student_id, True)
            except (NameError, AttributeError):  # AttributeError for hex record not exist
                return render_template('check.html', timetable=None)
        elif data['type'] == 'year-24':
            try:
                # The user input should be hex id now
                # student_id = get_hex_id(student_id)
                timetable, name = get_individual_timetable(url, student_id, False)
            except (NameError, AttributeError):  # AttributeError for hex record not exist
                return render_template('check.html', timetable=None)
        elif data['type'] == 'plan':
            try:
                timetable, name = get_plan_textspreadsheet(url, student_id)
            except NameError:
                return render_template('check.html', timetable=None)
        elif data['type'] == 'name':
            try:
                timetable, name = get_staff_timetable(url, student_id)
            except NameError:
                return render_template('check.html', timetable=None)
        else:
            return render_template('check.html', timetable=None)
        record = add_or_update(record, student_id, timetable, name, force_refresh)
    link = get_link()
    record.timetable = filter_semester(get_current_semester(), record.timetable)
    return render_template('check.html',
                           fields=fields,
                           timetable=record.timetable,
                           link=link,
                           name=record.sname,
                           timestamp=arrow.get(record.timestamp).to('Asia/Shanghai').humanize())


@bp.errorhandler(requests.exceptions.ConnectionError)
def handle_origin_site_down(e):
    return render_template('check.html', timetable=None,
                           errormsg='The school\'s official timetabling is not accessible.')

from datetime import timedelta
import arrow

from flask import Blueprint
from flask import current_app
from flask import jsonify
from flask import request
from flask import make_response

from nottingtable import db
from nottingtable.crawler.individual import validate_student_id
from nottingtable.crawler.individual import get_individual_timetable
from nottingtable.crawler.individual import generate_ics as get_ics_individual
from nottingtable.crawler.plans import get_plan_textspreadsheet
from nottingtable.crawler.plans import generate_ics as get_ics_plan
from nottingtable.crawler.models import User
from nottingtable.crawler.models import Course
from nottingtable.crawler.models import Y1Group
from nottingtable.crawler.models import MasterPlan

bp = Blueprint('api', __name__, url_prefix='/api')


def add_or_update(record, key, value, force_refresh):
    """
    Insert a new user record or update exist one
    :param force_refresh: if refresh is required
    :param value: the value ready for insertion and update
    :param key: the key in database
    :param record: a User record
    :return: updated record
    """

    if not record:
        db.session.add(User(student_id=key, timetable=value))
        db.session.commit()
    elif force_refresh:
        record.timetable = value
        record.timestamp = arrow.utcnow().datetime
        db.session.commit()
    record = User.query.filter_by(student_id=key).first()
    return record


def get_record(student_id, force_refresh):
    """
    Get record from cache database
    :param student_id: cache identifier
    :param force_refresh: force_refresh flag
    :return: student_record and force_refresh
    """
    student_record = User.query.filter_by(student_id=student_id).first()

    # cache life time check
    if student_record:
        last_update_time = arrow.get(student_record.timestamp)
        if arrow.utcnow() - last_update_time > timedelta(days=current_app.config['CACHE_LIFE']):
            force_refresh = 1
    else:
        force_refresh = 1

    return student_record, force_refresh


def output_timetable(format_type, record, ics_func, ics_name):
    """
    Return the timetable
    :param format_type: output format json/ical
    :param record: cached user record
    :param ics_func: the function to get ics file
    :param ics_name: ics filename
    :return: ics file or json response
    """
    if format_type == 'json':
        return jsonify(timetable=record.timetable, last_update=record.timestamp), 200
    elif format_type == 'ical':
        response = make_response((ics_func(record, current_app.config['FIRST_MONDAY']), 200))
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format('"' + ics_name + '.ics"')
        response.headers['Content-Type'] = 'text/calendar charset=utf-8'
        return response


@bp.route('/individual/<format_type>', methods=('GET',))
def get_individual_data(format_type):
    if format_type != 'json' and format_type != 'ical':
        return jsonify(error='Not Found'), 404
    if request.args.get('id'):
        student_id = request.args.get('id')
        is_year1 = False
    elif request.args.get('group'):
        student_id = request.args.get('group')
        is_year1 = True
    else:
        return jsonify(error='Student ID or Group Name Not Provided'), 400

    if not is_year1:
        if not validate_student_id(student_id, is_year1=is_year1):
            return jsonify(error='Student ID Invalid'), 400
    else:
        if not validate_student_id(student_id, is_year1=is_year1):
            return jsonify(error='Group Name Invalid'), 400

    force_refresh = request.args.get('force-refresh') or 0

    student_record, force_refresh = get_record(student_id, force_refresh)

    if not student_record or force_refresh:
        url = current_app.config['BASE_URL']
        try:
            timetable_list = get_individual_timetable(url, student_id, is_year1)
        except NameError:
            return jsonify(error='Student ID/Group Invalid'), 400

        student_record = add_or_update(student_record, student_id, timetable_list, force_refresh)

    return output_timetable(format_type, student_record, get_ics_individual, student_id)


@bp.route('/plan/<format_type>', methods=('GET',))
def get_plan_data(format_type):
    if format_type != 'json' and format_type != 'ical':
        return jsonify(error='Not Found'), 404

    plan_id = request.args.get('plan')
    if not plan_id:
        return jsonify(error='Plan not Provided'), 400

    force_refresh = request.args.get('force-refresh') or 0

    student_record, force_refresh = get_record(plan_id, force_refresh)

    if not student_record or force_refresh:
        url = current_app.config['BASE_URL']
        try:
            timetable_list = get_plan_textspreadsheet(url, plan_id)
        except NameError:
            return jsonify(error='Plan ID Invalid'), 400

        student_record = add_or_update(student_record, plan_id, timetable_list, force_refresh)

    return output_timetable(format_type, student_record, get_ics_plan, plan_id)


@bp.route('/activity', methods=('GET',))
def show_activity():
    name = request.args.get('name')

    if not name:
        return jsonify(error='Activity Name Not Provided'), 400

    activity_records = Course.query.filter_by(activity=name).all()

    return jsonify([i.serialize for i in activity_records]), 200


@bp.route('/module', methods=('GET',))
def show_module():
    name = request.args.get('name')

    if not name:
        return jsonify(error='Module Name Not Provided'), 400

    module_records = Course.query.filter_by(module=name).all()

    return jsonify([i.serialize for i in module_records]), 200


@bp.route('/year1-list', methods=('GET',))
def show_year1_list():
    year1_list = Y1Group.query.all()
    return jsonify([i.group for i in year1_list]), 200


@bp.route('/master-plan-list', methods=('GET',))
def show_master_plan_list():
    master_list = MasterPlan.query.all()
    return jsonify({i.plan_name: i.plan_id for i in master_list})

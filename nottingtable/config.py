import os
import arrow


class Config(object):
    DEBUG = False
    #DATABASE_URI='mysql+pymysql://uCourse:uCourse@127.0.0.1:3306/timetable'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'mysql+pymysql://root:Taylorswift@127.0.0.1:3306/timetable'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default url for timetabling service
    BASE_URL = 'http://timetablingunnc.nottingham.ac.uk:8017/'  # Last '/' cannot be omitted
    FIRST_MONDAY = arrow.get('2022-09-12')  # YYYY-MM-DD format

    # Default url for year1 group list
    #YEAR1_PDF_URL = 'https://www.nottingham.edu.cn/en/academicservices/documents/2020-2021-s2-year-1-student-timetable.pdf'
    YEAR1_PDF_URL = 'https://www.nottingham.edu.cn/en/academicservices/documents/year-1-student-timetable-2022-23-autumn-semester-0916v2.pdf'
    # integer, the cache lifetime in database, unit: day
    CACHE_LIFE = 365

    # Server domain
    SERVER_NAME = os.environ.get('SERVER_NAME')


class ProductionConfig(Config):
    BASE_URL = 'http://timetablingunnc.nottingham.ac.uk:8017/'


class DevelopmentConfig(Config):
    DEBUG = True

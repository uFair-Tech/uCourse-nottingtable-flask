import datetime
import threading
from time import sleep
import click
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
#实现规避检测
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By

from nottingtable import db
from nottingtable.crawler.models import Cookie


def get_cookie():
    #try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.page_load_strategy = 'eager'

        # 实现规避检测

        option = ChromeOptions()
        option.add_experimental_option('excludeSwitches', ['enable-automation'])

        # 实现让selenium规避被检测到的风险

        #chrome_options=chrome_options, options=option


        driver = webdriver.Chrome(
            executable_path='/Users/mayuhao/uCourse-nottingtable-flask/nottingtable/chromedriver',
            )
        driver.get("https://timetabling.nottingham.edu.cn/web/")
        sleep(2)
        input = driver.find_element(By.ID,'i0116')
        print(3)
        # input email
        input.send_keys('UNNC_email')
        print(4)
        button1 = driver.find_element(By.ID, 'idSIButton9')

        button1.click()
        sleep(4)
        pw = driver.find_element(By.ID, 'passwordInput')
        # inuput password
        print(5)
        pw.send_keys('pw')
        print(6)
        button2 = driver.find_element(By.ID, 'submitButton')
        button2.click()
        button3 = driver.find_element(By.ID, 'idSIButton9')
        button3.click()
        cookie = driver.get_cookies()[0]
        return cookie['value']
    
    
    #except:
     #   print("fail connect!!!")
     #   sleep(5)
      #  get_cookie()




def initial_request_cookies():
    cookie = get_cookie()
    Cookie.__table__.drop(db.engine)
    Cookie.__table__.create(db.engine)
    db.session.add(Cookie(cookie=cookie))
    db.session.commit()
    click.echo('cookie Updated!')
    """
    timer = threading.Timer(3600,request_cookies)
    timer.start()
    """

def update_cookies(app):
    with app.app_context():
        """
        new_cookie = get_cookie()
        old_cookie = Cookie.query.first()
        old_cookie.cookie = new_cookie
        """
        #try:
        new_cookie = get_cookie()
        #db.session.query(Cookie).filter_by(id=1).delete()
        #db.session.add(Cookie(cookie=new_cookie))
        #db_cookie = db.session.query(Cookie).filter_by(id=1).first()
        #print("old db ", db_cookie.cookie)
        db.session.query(Cookie).filter_by(id=1).update({Cookie.cookie:new_cookie})
        db.session.commit()
        print(new_cookie)
        db_cookie = db.session.query(Cookie).filter_by(id=1).first()
        print("db ",db_cookie.cookie)
        now = datetime.datetime.now()
        ts = now.strftime('%H:%M:%S')
        print("Done", ts)
        timer = threading.Timer(3500,update_cookies,(app,))
        timer.start()
        #except:
            #update_cookies(app)

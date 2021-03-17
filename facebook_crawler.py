# -*- coding: UTF-8 -*- 
# facebook crawler
# facebook address example: https://www.facebook.com/weather.taiwan/
# 抓取臉書社團前一個月，社團成員分享文章次數。

from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re, time, requests
import datetime
import calendar
import pandas as pd
import os

# 貼文連結
def Wall_PostLink(i):
    Link = 'https://www.facebook.com' + i.find('a',{'class':'_5pcq'}).attrs['href'].split('?',2)[0]
    return Link
#取得頁面最早貼文的時間
def Earliest_Post_time(postContent):
    return datetime.datetime.fromtimestamp(int(postContent[len(postContent)-1].find('abbr').attrs['data-utime']))

def Wall_PostID(Post):
    ID = Post.find('img').attrs['aria-label']
    return ID

def Post_Time(Post):
    return datetime.datetime.fromtimestamp(int(Post.find('abbr').attrs['data-utime']))

#時間設定
today = datetime.datetime.today()
datem = datetime.datetime(today.year, today.month-1, 1)
year = today.year
month = today.month-1
days = calendar.monthrange(year,month)[1]
month = '%02d' % month
datestart = f'{year}-{month}-01'
datestart = datetime.datetime.strptime(datestart,'%Y-%m-%d')
dateend = datestart+datetime.timedelta(days=days-1)

#設定禁止彈出視窗
options = Options()
options.add_argument("--disable-notifications")

driver = webdriver.Chrome(chrome_options=options, executable_path='C:\chromedriver.exe')
driver.get("http://www.facebook.com")  #開啟臉書
time.sleep(3)

account = '輸入臉書帳號:'
password = '輸入臉書密碼:'

#login facebook
driver.find_element_by_id("email").send_keys(f'{account}')    #輸入帳號 
driver.find_element_by_id("pass").send_keys(f'{password}')     #輸入密碼
driver.find_element_by_id("loginbutton").click()
time.sleep(3)
#進入指定社團
driver.get('https://zh-tw.facebook.com/8518go/')  #<--------- 替換為你需要的臉書社團網址
time.sleep(5)

soup = BeautifulSoup(driver.page_source)
posts = soup.findAll('div', {'class':'_5pcr userContentWrapper'})

earliest_time = Earliest_Post_time(posts)
#捲動視窗直到現有頁面的最早貼文小於指定月份
while earliest_time >= datestart:
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    soup = BeautifulSoup(driver.page_source)
    posts = soup.find_all('div', {'class':'_5pcr userContentWrapper'})
    earliest_time = Earliest_Post_time(posts)
    print(earliest_time)
len(posts)

#獲取每則貼文時間與網址
url_lst = []
post_ids = []
post_times = []
for post in posts:
    url = Wall_PostLink(post)
    post_id = Wall_PostID(post)
    post_time = Post_Time(post)
    
    url_lst.append(url)
    post_ids.append(post_id)
    post_times.append(post_time)

print(f'Crawling {year}-{month} post url ------------- end ' + '-'*15 + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
len(url_lst)

post_info = pd.DataFrame(dict(post_id=post_ids, post_time=post_times, url=url_lst))
#保留當月份貼文
post_info = post_info.loc[(post_info['post_time'] >= datestart) &  (post_info['post_time'] <= dateend)].reset_index(drop=True).copy()

# ------------ 獲取各個貼文的轉貼分享ID與時間 --------------------------------------------------------------------------------
out_df = pd.DataFrame()
for i in range(len(post_info)):
    t1 = time.time()
    url = post_info['url'][i]
    post_time = posts[len(posts)-1].find('abbr').attrs['data-utime']
    post_time = datetime.datetime.fromtimestamp(int(post_time))  #unix time to datetime
    post_time = post_time.strftime("%Y-%m-%d %H:%M")
    print(f'正在處理第{i+1}則貼文, 發文時間:{post_time}, 網址:' + url +'\n------------------' )
    driver.get(url)
    time.sleep(5)
    try:
        driver.find_element_by_xpath("//span[@class='_355t _6iik'][@data-hover='tooltip']").click()
        time.sleep(5)
    except:
        driver.find_element_by_xpath("//span[@class='_355t _4vn2'][@data-hover='tooltip']").click()
        time.sleep(5)
    SCROLL_PAUSE_TIME = 0.5
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")    
    while True:
        # Scroll down to bottom
        print(f'上次頁面高度:{last_height}')
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    
        # Wait to load page
        time.sleep(4)
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        print(f'本次頁面高度:{new_height}')
        time.sleep(1)
        print('Time Log: ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n\n------------------')
    print('This re-post content can not expand')

    content = BeautifulSoup(driver.page_source)
    
    # 轉發此貼文區塊
    shareContent = content.find('div', {'class':'_4-i2 _pig _5ki2 _50f4'})
    # 分享者資訊區塊
    Posterblock = shareContent.findAll('div', {'class':'_4-u2 mbm _4mrt _5jmm _5pat _5v3q _7cqq _4-u8'})

    share_ids = []
    share_times = []
    for Poster in Posterblock:
        shareID = re.findall('_6a _5u5j _6b.*?href=".*?">(.*?)</a>', str(Poster))[0]
        print(shareID)
        shareTime = Post_Time(Poster) 
         
        share_ids.append(shareID)
        share_times.append(shareTime)
        
    df = pd.DataFrame(dict(User_ID=share_ids, Datetime=share_times))
    df = df.loc[(df['Datetime'] >= datestart) &  (df['Datetime'] <= dateend)].reset_index(drop=True).copy()
    out_df = out_df.append(df)
    t2 = time.time()
    print(f'第{i+1}則貼文解析完成, 進度:{((i+1)/len(post_info)):.0%}', '='*20, datetime.datetime.now().strftime("%H:%M:%S"), '=============== takes time:', str(round(t2 - t1)) +'sec','\n------------------' )
print('='*15,f'{year}年{month}月 轉貼分享次數計算 == END === Time:', datetime.datetime.now().strftime("%H:%M:%S") ,'=======================') 

#計算每個ID分享次數
table = out_df.groupby(['User_ID'])['User_ID'].count().reset_index(name ='分享次數')
table = table.sort_values(by=['分享次數','User_ID'], ascending=False).reset_index(drop = True).copy()

#輸出檔案 ----------------------
''' 
說明:
file_path: 檔案輸出的資料夾路徑，改成你要放的資料夾路徑
file_name: facebook_share_count_{year}_{month}.csv ---> year與month不要更動，其他可修改
'''
path = os.environ['USERPROFILE']
folder_path = f'{path}'  # ex: C:/Users/username/Desktop
file_name = f'\\facebook_share_count_{year}_{month}.csv'
table.to_csv(os.environ['USERPROFILE']+'\\Desktop' + file_name, encoding='UTF-8',index=False)



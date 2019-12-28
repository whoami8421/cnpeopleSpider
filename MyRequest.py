# from hashlib import md5
# import base64
# import os
# import chardet
import time
import random
import requests
import traceback
from tools import cntools

user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; …) Gecko/20100101 Firefox/61.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
]
headers = {}

def RequestGet(url, timeout = 1, retry_times=3,sleep_time = 0):
    res = None
    if retry_times > 0:
        for i in range(retry_times):
            try:
                headers['User-Agent'] = random.choice(user_agent_list)
                res = requests.get(url, timeout=timeout,headers=headers)
                break
            except:
                #traceback.print_exc()
                time.sleep(sleep_time)
    else:
        try:
            res = requests.get(url, timeout=timeout)
        except:
            traceback.print_exc()
            time.sleep(sleep_time)
    return res

if __name__=='__main__':
    res = RequestGet('http://search.people.com.cn/cnpeople/search.do?siteName=news&pageNum=1&facetFlag=true&nodeType=belongsId&nodeId=0&keyword=%B8%BB%B4%A8')
    res.encoding = cntools.GetCharset(res.content)
    print(res.text)
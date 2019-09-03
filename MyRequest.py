# from hashlib import md5
# import base64
# import os
# import chardet
import time
import requests
import traceback
from tools import cntools


def RequestGet(url, timeout = 1, retry_times=3,sleep_time = 0):
    res = None
    if retry_times > 0:
        for i in range(retry_times):
            try:
                res = requests.get(url, timeout=timeout)
                break
            except:
                traceback.print_exc()
                time.sleep(sleep_time)
    else:
        try:
            res = requests.get(url, timeout=timeout)
        except:
            traceback.print_exc()
            time.sleep(sleep_time)
    return res

if __name__=='__main__':
    res = RequestGet('http://www.baidu.com')
    res.encoding = cntools.GetCharset(res.content)
    print(res.text)
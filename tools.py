from hashlib import md5
import base64
import os
import chardet
import time

class cntools:
    def __init__(self):
        pass
    @staticmethod
    def StrToMD5(text):
        return md5(text.encode('utf-8')).hexdigest()
    @staticmethod
    def StrToBase64(text):
        raw = base64.b64encode(text.encode('utf-8'))
        result = str(raw)[2:-1]
        return result
    @staticmethod
    def GetCharset(content):
        return chardet.detect(content)['encoding']
    @staticmethod
    def NumListCut(start,end,cut_len) -> list:
        result = []
        s = start
        e = end
        if s>=e:
            result.append((start,start))
            return result
        while(1):
            if s+cut_len>e:
                result.append((s,e))
                return result
            else:
                result.append((s,s+cut_len-1))
                s+=cut_len
                if s  > e:
                    result.append((s, e))
                    return result
    @staticmethod
    def logger(text,log_file=None,if_write = True):
        time_stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        log_data = f'{time_stamp}: {text}\n'
        print(log_data)
        if not if_write:
            return
        if log_file:
            path = log_file[:log_file.rfind('/')]
            file = log_file[log_file.rfind('/'):]
        else:
            path = './log/'
            file = 'log.txt'
        if not os.path.exists(path):
            os.makedirs(path)
        save_file = path+file
        fp = open(save_file,'a')
        fp.write(log_data)
        fp.close()






if __name__=='__main__':

    print(os.path.exists('./log/kl.txt'))


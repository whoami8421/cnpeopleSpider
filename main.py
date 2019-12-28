# python 3
# -*- coding:utf-8 -*-

import requests
from urllib import parse
from bs4 import BeautifulSoup
import os,re
import queue
import threading
import time
import traceback
import tools
import random
from math import ceil
from MyRequest import RequestGet

# 根据关键词爬取数据
# 并生成相应的数据目录结构存放
class cnpeople:


    def __init__(self):
        # 关键词列表
        self.keywords = ['成都',]
            # ['德阳','都江堰','彭州','崇州','邛崃','简阳',
            #             '江油','广汉','什邡','绵竹','隆昌',
            #             '峨眉山','阆中','万源','马尔康',
            #             '康定','西昌','华蓥',]

        self.MainUrlList = []
        self.HostHeader = 'http://search.people.com.cn'
        self.BaseDir = os.path.dirname(__file__).replace('\\','/')
        # 页面url任务队列
        self.PageUrlQueue = queue.Queue()
        self.PageUrlQueueLock = threading.Lock()
        # 线程数设置
        self.PageUrlThreads = 4
        self.AnalyseThreads = 20
        self.PicDownloadThreads = 10
        self.WriteDataThreads = 8
        # 文章url队列，后期注意大小分配
        self.ArticleUrlQueue = queue.Queue()
        self.ArticleUrlQueueLock = threading.Lock()
        # 写入数据队列，字典类型{}
        self.WriteDataQueue = queue.Queue()
        self.WriteDataQueueLock = threading.Lock()
        self.WriteDataLock = threading.Lock()
        # 图片队列，保存每个片的url和存储位置信息，字典类型
        self.PicturesQueue = queue.Queue()
        self.PicturesQueueLock = threading.Lock()
        self.QueueTimeout = 1
        self.count = 0
        self.ErrorResponse=[
            'http://search.people.com.cn/cnpeople/news/error.jsp',
            'http://search.people.com.cn/cnpeople/news/noNewsResult.jsp'
        ]
        self.ErrorNullUrl = 'http://search.people.com.cn/cnpeople/news/error.jsp'
        self.NoReUrl = 'http://search.people.com.cn/cnpeople/news/noNewsResult.jsp'
        self.filter_box = [
            '/img/prev_page.jpg',
            '/img/next_page.jpg',
            '20170418/62/10124098537665804450.jpg',
            '/img/2016wb/images/code_wx.jpg',
            '/mediafile/pic/20160108/23/3945047742616879703.jpg',
            '/mediafile/201206/',
        ]
        self.url_filter = []
        for keyword in self.keywords:
            param = {'keyword': keyword}
            url = parse.urlencode(param, encoding='gb2312')
            self.MainUrlList.append(
                'http://search.people.com.cn/cnpeople/search.do?siteName=news&pageNum=1&facetFlag=true&nodeType=belongsId&nodeId=0&' + url)

            self.user_agent_list = [
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; …) Gecko/20100101 Firefox/61.0",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
                "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
                "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
                "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
                ]
            self.headers={}
            self.headers['User-Agent'] = random.choice(self.user_agent_list)
            #获取分栏线程的状态，初始化为True
            self.GetPageThreadsEvent = threading.Event()
            self.GetPageThreadsEvent.set()
            # 文章解析线程的状态，初始化为True
            self.ArticleAnalysEvent = threading.Event()
            self.ArticleAnalysEvent.set()
            self.ArticleAnalysThreadList = []

    # get first pagelist
    # 搜索页面下的每个分栏
    # {url:save_path}

    def PicFilter(self,pic_url):
        if_raw = True
        for f in self.filter_box:
            if (f in pic_url):
                if_raw = False
                break
        if if_raw:
            return pic_url
        else:
            return None
    def GetFirstPage(self,url) -> dict:
        try:
            self.headers['User-Agent'] = random.choice(self.user_agent_list)
            res = requests.get(url,headers=self.headers)
            res.encoding = 'GB2312'
        except:
            print('FirstPage Error.')
            traceback.print_exc()
            return {}
        main_html = BeautifulSoup(res.text,'html5lib')
        res = main_html.find('div', class_='fl w180')
        search_box = main_html.find('div', class_='searchbar_text')
        keyword = search_box.font.text
        child_list = res.find_all('li')
        result_dict = {}
        for child in child_list:

            child_path = child.a.text[:child.a.text.rfind('(')].strip('\r\n\t')
            save_path = self.BaseDir + '/data/' + keyword + '/' + child_path + '/'
            page_url = self.HostHeader+child.a['href']
            result_dict[page_url]=save_path

        return result_dict


    #初始化PageQueue列表
    def PageInIt(self,main_url):
        print('初始化页面数据')
        pattern = re.compile(r'本次检索为您找到 <b>(\d+?)</b> .+? 的页面,用时.+秒')
        res = RequestGet(main_url)
        if not res:
            print('failed.')
            return {}
        res.encoding = 'GB2312'
        main_html = BeautifulSoup(res.text,'html5lib')
        res = main_html.find('div', class_='fl w180')
        search_box = main_html.find('div', class_='searchbar_text')
        keyword = search_box.font.text
        child_list = res.find_all('li')
        for child in child_list:

            child_path = child.a.text[:child.a.text.rfind('(')].strip('\r\n\t')
            save_path = self.BaseDir + '/data/' + keyword + '/' + child_path + '/'
            page_url = self.HostHeader+child.a['href']
            print('{}/{}:{}'.format(keyword,child_path,page_url))
            if_continue = False
            for i in range(3):
                try:
                    self.headers['User-Agent'] = random.choice(self.user_agent_list)
                    page_res = requests.get(url=page_url,headers = self.headers)
                except:
                    if i==2:
                        break
                    continue
                if page_res.url == self.NoReUrl or not page_res:
                    if_continue = True
                    break
                if page_res.url == self.ErrorNullUrl:
                    time.sleep(0.5)
                    if i == 2:
                        if_continue = True
                    continue
                break
            if if_continue:
                continue
            page_res.encoding = 'GB2312'
            # print('main_url = {}\nres.url = {}'.format(main_url,page_res.url))
            page_count = int(pattern.findall(page_res.text)[0])
            data = {
                'page_url': page_url,
                'url_count': page_count,
                'save_path': save_path
            }
            #tools.cntools.logger(str(data),log_file='./log/count.txt')

            while(True):
                try:
                    #self.PageUrlQueueLock.acquire()
                    self.PageUrlQueue.put(data,timeout=1)
                    #self.PageUrlQueueLock.release()
                    break
                except queue.Full:
                    #self.PageUrlQueueLock.release()
                    print('PageUrlQueue is Full.')
                    time.sleep(1)
                    continue
        print('页面初始化完成 ')



    #获取文章页的url列表，单线程模式,自带迭代下一页
    def GetContentUrls(self,start_url,save_path):
        #print(f'get content url:{start_url}')
        while(True):
            self.headers['User-Agent'] = random.choice(self.user_agent_list)
            res = requests.get(start_url,headers = self.headers)
            res.encoding = 'GB2312'
            main_html = BeautifulSoup(res.text,'html5lib')
            if_error = main_html.find('img', alt='Error')
            if_value = main_html.find('h3', class_='ts0328')
            if not if_value and not if_error and res:
                break
        url_list = []
        result = main_html.find('div', class_='fr w800')
        #print('len = {}'.format(len(res.text)))
        urls = result.find_all('b')
        urls.remove(urls[0])
        # 去重+筛选
        filt = ['http://renwu', 'http://lottery']
        for url in urls:
            if url.a['href'] not in url_list:
                if_use = True
                for f in filt:
                    if url.a['href'].startswith(f):
                        if_use = False
                if if_use:
                    url_list.append(url.a['href'])
        for url in url_list:
            data = {
                'save_path':save_path,
                'article_url':url
            }
            #print('put data:{},size = {}'.format(data,self.ArticleUrlQueue.qsize()))
            #print('put article_url:{}'.format(data))

            while(True):
                try:
                    #self.ArticleUrlQueueLock.acquire()
                    self.ArticleUrlQueue.put(data,timeout=1)
                    #self.ArticleUrlQueueLock.release()
                    break
                except queue.Full:
                    #self.ArticleUrlQueueLock.release()
                    print('ArticleUrlQueue is Full.')
                    time.sleep(1)
                    continue
        page_box = result.find('div', class_='show_nav_bar')
        if not page_box:
            return
        else:
            page_list = page_box.find_all('a')
            for page in page_list:
                # if page.text == '11':
                #     return
                if page.text == '下一页':
                    next_url = self.HostHeader + page['href']
                    # 递归或迭代
                    self.GetContentUrls(next_url,save_path)

    def GetContentUrlsRange(self,start_url,range_tuple,save_path):

        repd = start_url[start_url.find('pageNum=') :start_url.find('&')]
        for page_num in range(int(range_tuple[0]),int(range_tuple[1])+1):

            page_url = start_url.replace(repd,'pageNum='+str(page_num))
            page_url = page_url.replace('&dateFlag=false','')

            #tools.cntools.logger(f'{save_path}:{page_url}','./urlcount.txt')
            #print(f'merge url = {page_url}')
            if_continue = False
            for i in range(3):
                res = RequestGet(page_url)
                if not res:
                    if_continue=True
                    break
                if res.url == self.ErrorNullUrl:
                    continue
                if res.url == self.NoReUrl:
                    if_continue = True
                    break
                if (i > 2):
                    if_continue = True
                break
            if if_continue:
                print('continue.')
                continue
            res.encoding = 'GB2312'
            main_html = BeautifulSoup(res.text,'html5lib')
            url_list = []
            result = main_html.find('div', class_='fr w800')
            urls = result.find_all('b')
            urls.remove(urls[0])
            # 去重+筛选
            filt = ['http://renwu', 'http://lottery']
            t1 = time.time()
            for url in urls:

                if url.a['href'] not in url_list:
                    if_use = True
                    for f in filt:
                        if url.a['href'].startswith(f):
                            if_use = False
                    if if_use:
                        url_list.append(url.a['href'])
            for url in url_list:

                data = {
                    'save_path':save_path,
                    'article_url':url
                }
                #print('put data:{},size = {}'.format(data,self.ArticleUrlQueue.qsize()))
                #print('put article_url:{}'.format(data))

                while(True):
                    try:


                        #self.ArticleUrlQueueLock.acquire()
                        #with threading.RLock():

                        self.ArticleUrlQueue.put(data,timeout=1)
                        #print(f'put data={data}')
                        # self.ArticleUrlQueueLock.release()
                        break
                    except queue.Full:
                        #self.ArticleUrlQueueLock.release()
                        print('ArticleUrlQueue is Full.')
                        time.sleep(1)
                        continue
            t3 = time.time()
        return


    def GetPageThreads(self):
        if_start = True
        child_threads =[]
        while(True):
            #print('GetPageThreads,获取分栏数据并开启线程')
            try:
                #self.PageUrlQueueLock.acquire()
                data = self.PageUrlQueue.get(timeout=1)
                #self.PageUrlQueueLock.release()
            except queue.Empty:
                #self.PageUrlQueueLock.release()
                #开始标志位1，子线程为空，说明page初始化未抓取到数据
                if if_start and not child_threads:
                    print('init page failed.')
                    return
                if child_threads:
                    if_end = True
                    for thread in child_threads:
                        if(thread.is_alive()):
                            if_end = False
                    #子线程均已结束，通知下一级线程并返回
                    if if_end:
                        #在此通知下一线程
                        #code
                        self.GetPageThreadsEvent.clear()
                        print('分栏线程均已退出.')
                        return
                else:
                    continue

            if_start = False
            start_url = data['page_url']
            save_path = data['save_path']
            url_count = data['url_count']
            page_count = ceil(url_count/20)
            cut_len = ceil(page_count/self.PageUrlThreads)
            #print(f'{page_count},{cut_len}')
            #print(f'计算分组,总页数:{page_count}')
            cut_list = tools.cntools.NumListCut(1,page_count,cut_len)
            #print(f'分组完成：{cut_list}')
            for tuple_range in cut_list:
                #间隔5s检测，保证子线程不多于4个
                #print('开启分栏线程')
                while(len(child_threads)>self.PageUrlThreads):
                    #print(f'分栏线程数{len(child_threads)}>{self.PageUrlThreads}，等待')
                    exit_threads=[]
                    for thread in child_threads:
                        if not thread.is_alive():
                            exit_threads.append(thread)
                    for e_t in exit_threads:
                        child_threads.remove(e_t)
                    time.sleep(1)

                t = threading.Thread(target=self.GetContentUrlsRange(start_url,tuple_range,save_path))
                t.start()
                #print('线程已开启')
                child_threads.append(t)

    # get pictures url list from str_TAG area
    def getPicUrls(self,main_url,str_TAG,save_path):
        #print('get_pic_urls.')
        result=[]
        host_url = re.compile(r'http.+?people\.com\.cn').findall(main_url)[0]
        pic = re.compile(r'src="(.+?\.jpg)"').findall(str_TAG)
        pic_JPG = re.compile(r'src="(.+?\.JPG)"').findall(str_TAG)
        pic = pic+pic_JPG
        for url in pic:
            pic_url = url
            if not url.startswith('http'):
                pic_url = host_url+url
            pic_url = self.PicFilter(pic_url)
            if not pic_url:
                continue
            result.append(pic_url)
            pic_data = {
                'pic_url':pic_url,
                'save_path':save_path
            }
            while(True):
                try:
                    #print('pic ac')
                    #self.PicturesQueueLock.acquire()
                    #print('pic in')
                    self.PicturesQueue.put(pic_data,timeout=1)
                    #self.PicturesQueueLock.release()
                    break
                    #print('pic out')
                except queue.Full:
                    #self.PicturesQueueLock.release()
                    print('PicturesQueue is Full.')
                    time.sleep(1)
                    continue
        #print('get_pic_urls.out')
        return result

    # 根据文章结构进行处理
    def ArticleAnalys(self,name):
        while(True):
            try:
                #取数据,注意处理队列为空的情况
                print(f'Thread ({name}): '
                      f'分页url：{self.PageUrlQueue.qsize()},'
                      f'文章url：{self.ArticleUrlQueue.qsize()}'
                      #f'写入数据：{self.WriteDataQueue.qsize()},'
                      #f'图片：{self.PicturesQueue.qsize()}'
                      )
                count = 5
                if_continue = False
                while(True):
                    try:
                        #self.ArticleUrlQueueLock.acquire()
                        #print('count = {}'.format(count))
                        ArticleData = self.ArticleUrlQueue.get(timeout=self.QueueTimeout)
                        #print(f'get article data:{ArticleData}')
                        # self.count+=1
                        # print('count = {}'.format(self.count))
                        #self.ArticleUrlQueueLock.release()
                        break
                    except queue.Empty:
                        # self.ArticleUrlQueueLock.release()
                        page_event = self.GetPageThreadsEvent.wait(1)
                        if not page_event:
                            print('数据data获取完毕.')
                            return
                        count=count-1
                        #print('ArticleUrlQueue is Empty.')
                        if count<0:
                            if_continue = True
                            break
                            # print('ArticleAnalys is exit.')
                            # return
                        time.sleep(1)
                        continue
                if if_continue:
                    continue
                article_url = ArticleData['article_url']
                save_path = ArticleData['save_path']
                if_continue = False

                try:
                    res = RequestGet(article_url,timeout = 1)
                    if not res:
                        if_continue = True
                except:
                    #self.headers['User-Agent'] = random.choice(self.user_agent_list)
                    print('ArticleAnalys request error.')

                if if_continue:
                    continue
                res.encoding = 'GB2312'
                html = BeautifulSoup(res.text, 'html5lib')
                leaders = html.find('div', class_='box_con')
                picchina = html.find('div', class_='content clear clearfix')
                health = html.find('div', class_='artDet')
                npc = html.find('div', id='p_content')
                cppcc = html.find('font', class_='show_c')
                picHealth = html.find('div', class_='text width978 clearfix')
                last_data = {
                    'article':'',
                    'pic_urls':[]
                }
                this_data = {
                    'save_path':save_path,
                    'article_url':article_url,
                    'html':html
                }
                # print('picHealth={},picchina={}'.format(picHealth,picchina))
                if leaders:
                    #print('put to leaders.\n')
                    try:
                        self.leaders(last_data,this_data)
                    except:
                        tools.cntools.logger('leaders()--'+traceback.format_exc())
                if picchina:
                    #print('put to picchina.\n')
                    try:
                        self.picchina(last_data,this_data)
                    except:
                        tools.cntools.logger('picchina()--'+traceback.format_exc())
                if health:
                    #print('put to health.\n')
                    try:
                        self.health(last_data,this_data)
                    except:
                        tools.cntools.logger('health()--'+traceback.format_exc())

                if npc:
                    #print('put to npc.\n')
                    try:
                        self.npc(last_data,this_data)
                    except:
                        tools.cntools.logger('npc()--'+traceback.format_exc())

                if cppcc:
                    #print('put to cppcc.\n')
                    try:
                        self.cppcc(last_data,this_data)
                    except:
                        tools.cntools.logger('cppcc()--'+traceback.format_exc())

                if picHealth:
                    #print('put to picHeath.\n')
                    try:
                        self.picHealth(last_data,this_data)
                    except:
                        tools.cntools.logger('picHealth()--'+traceback.format_exc())

                if not (leaders
                        or picchina
                        or health
                        or npc
                        or cppcc
                        or picHealth
                ):
                    # print('leasers={}\npicchina={}\nhealth={}\nnpc={}\n'.format(leaders,picchina,health,npc))
                    print('url not in.')
                    fp = open('other_url.txt', 'a')
                    fp.write(this_data['article_url'] + '\n')
                    fp.close()
            except:
                print('Analyse 线程中断！')
                tools.cntools.logger(traceback.format_exc())

    # leaders,society,politics(时政),finance,IT,legal,travel新版网页
    # 备注：人物（renwu）,lottery分栏的链接无法访问
    def leaders(self,last_data, this_data):
        pic_urls = last_data['pic_urls']
        article = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        body_tag = html.find('div', class_='box_con')
        if not body_tag:
            print(f'function leaders(),url = {article_url}')
            print('leaders bodytag is null.')
            return
        str_TAG = str(body_tag)
        picUrlList = self.getPicUrls(article_url, str_TAG,save_path)

        body_list = body_tag.find_all('p')
        #print('body_len={}'.format(len(body_list)))
        for body in body_list:
            article += body.text
        picUrlList += pic_urls
        if_next = html.find('img', src='/img/next_page.jpg')
        if if_next:
            next_url = if_next.parent['href']
            host_url = re.compile(r'http.+?people\.com\.cn').findall(article_url)[0]
            if not next_url.startswith('http'):
                next_url = host_url + next_url
            last_data['article'] = article
            last_data['pic_urls'] = picUrlList
            self.headers['User-Agent'] = random.choice(self.user_agent_list)
            res = requests.get(next_url,headers = self.headers)
            res.encoding = 'GB2312'
            html = BeautifulSoup(res.text,'html5lib')
            this_data['html'] = html
            self.leaders(last_data,this_data)
        else:
            text_title = html.find('div', class_='clearfix w1000_320 text_title')
            from_msg = text_title.find('div', class_='fl')
            if not text_title:
                text_title = html.find('div', class_='content_bg w960 clearfix')
                from_msg = text_title.find('h5')
            from_msg = from_msg.text
            title_pre = text_title.find('h3').text
            main_title = text_title.find('h1').text
            title_sub = text_title.find('h4').text
            author = text_title.find('p', class_='author').text
            title_list = [title_pre, main_title, title_sub, author]
            title_msg = ''
            for title in title_list:
                if title:
                    title_msg += (title + '\n')
            title_msg = title_msg.strip(' \n')
            edit = html.find('div', class_='edit clearfix')
            edit = edit.text
            item = {}
            item['title'] = title_msg
            item['article'] = article + '\n' + edit
            item['from_msg'] = from_msg
            item['article_url'] = article_url
            item['pic_urls'] = picUrlList
            item['save_path'] = save_path
            while(True):
                try:
                    #self.WriteDataQueueLock.acquire()
                    self.WriteDataQueue.put(item,timeout=1)
                    #print('put write data = {}'.format(item))
                    #self.WriteDataQueueLock.release()
                    break
                except queue.Full:
                    #self.WriteDataQueueLock.release()
                    print('WriteDataQueue is Full.')
                    time.sleep(1)
                    continue
            return

    # 人民健康网
    def health(self, last_data, this_data):
        pic_urls = last_data['pic_urls']
        article = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        title_msg = html.find('div', class_='title')

        title_msg = title_msg.text
        from_msg = html.find('div', class_='artOri').text
        art_tag = html.find('div', class_='artDet')
        art_body = art_tag.text
        editor = html.find('div', class_='editor').text
        article = art_body + '\n' + editor
        pic_urls = self.getPicUrls(article_url, str(art_tag),save_path)
        item = {}
        item['title'] = title_msg
        item['article'] = article
        item['from_msg'] = from_msg
        item['article_url'] = article_url
        item['pic_urls'] = pic_urls
        item['save_path'] = save_path
        while (True):
            try:
                #self.WriteDataQueueLock.acquire()
                self.WriteDataQueue.put(item,timeout=1)
                #print('put write data = {}'.format(item))
                #self.WriteDataQueueLock.release()
                break
            except queue.Full:
                #self.WriteDataQueueLock.release()
                print('WriteDataQueue is Full.')
                time.sleep(1)
                continue
        return

    # 图片展区网页http://health.people.com.cn/n1/2019/0617/c14739-31156180.html
    def picHealth(self, last_data,this_data):
        pic_urls = last_data['pic_urls']
        article = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        print('picHeath url:{}'.format(article_url))
        main_tag = html.find('div', class_='text width978 clearfix')
        pic_urls += self.getPicUrls(article_url, str(main_tag),save_path)
        # print('main_tag={}'.format(main_tag))
        art_list = main_tag.find_all('p', class_='text-indent: 2em;')
        for art in art_list:
            article += art.text
        next_tags = main_tag.find_all('td')
        if_next = False
        for next_tag in next_tags:
            if next_tag.text == '下一页':
                if_next = True
                next_url = next_tag.a['href']
                host_url = re.compile(r'http.+?people\.com\.cn').findall(article_url)[0]
                if not next_url.startswith('http'):
                    next_url = host_url + next_url
                last_data['article'] = article
                last_data['pic_urls'] = pic_urls
                self.headers['User-Agent'] = random.choice(self.user_agent_list)
                res = requests.get(next_url,headers = self.headers)
                res.encoding = 'GB2312'
                html = BeautifulSoup(res.text, 'html5lib')
                this_data['html'] = html
                self.picHealth(last_data, this_data)
        if not if_next:
            title = main_tag.find('h1').text
            from_msg = main_tag.find('h2').text
            editor = main_tag.find('i', id='p_editor').text
            item = {}
            item['title'] = title
            item['article'] = article + '\n' + editor
            item['from_msg'] = from_msg
            item['article_url'] = article_url
            item['pic_urls'] = pic_urls
            item['save_path'] = save_path
            while (True):
                try:
                    #self.WriteDataQueueLock.acquire()
                    self.WriteDataQueue.put(item,timeout=1)
                    #print('put write data = {}'.format(item))
                    #self.WriteDataQueueLock.release()
                    break
                except queue.Full:
                    #self.WriteDataQueueLock.release()
                    print('WriteDataQueue is Full.')
                    time.sleep(1)
                    continue
            return

    # 旧版人大新闻网、旧版人民网招商频道、旧版开放区、领导分区
    def npc(self, last_data,this_data):
        pic_urls = last_data['pic_urls']
        article = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        title_msg = html.find('h1', id='p_title')
        title_msg = title_msg.text
        time_tag = html.find('i', id='p_publishtime')
        if not time_tag:
            time_tag = html.find('span', id='p_publishtime')
        if time_tag:
            p_time = time_tag.text
        else:
            p_time=''
        origin_tag = html.find('i', id='p_origin')
        if not origin_tag:
            origin_tag = html.find('span', id='p_origin')
        p_origin = origin_tag.text
        from_msg = f'{p_time} {p_origin}'
        body_list = html.find_all('div', class_='show_text')
        art_body = ''
        if len(body_list) > 1:
            p_list = body_list[0].find_all('p', style='text-indent:2em;')
            for p in p_list:
                art_body += p.text
        else:
            art_tag = html.find('div', id='p_content')
            art_body = art_tag.text
            pic_urls += self.getPicUrls(article_url, str(art_tag),save_path)
        editor_tag = html.find('div', id='p_editor')
        if not editor_tag:
            editor = ''
        else:
            editor = html.find('div', id='p_editor').text
        article += art_body + '\n' + editor

        item = {}
        item['title'] = title_msg
        item['article'] = article
        item['from_msg'] = from_msg
        item['article_url'] = article_url
        item['pic_urls'] = pic_urls
        item['save_path'] = save_path
        while (True):
            try:
                #self.WriteDataQueueLock.acquire()
                self.WriteDataQueue.put(item,timeout=1)
                #print('put write data = {}'.format(item))
                #self.WriteDataQueueLock.release()
                break
            except queue.Full:
                #self.WriteDataQueueLock.release()
                print('WriteDataQueue is Full.')
                time.sleep(1)
                continue
        return

    # 图说中国、图片频道、华人华侨（图片）
    def picchina(self, last_data,this_data):
        pic_urls = last_data['pic_urls']
        LastArticle = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        body = html.find('div', class_='content clear clearfix')
        article = ''
        for tag in body.find_all('p'):
            article += tag.text
        pic_tag = html.find('div', class_='pic_content clearfix')
        jpgList = self.getPicUrls(article_url, str(pic_tag),save_path)
        JPGList = self.getPicUrls(article_url, str(body),save_path)
        picUrlList = jpgList + JPGList
        # print('jlist={},Jlist={},flist={}'.format(jpgList,JPGList,picUrlList))
        # input('stop')
        picUrlList += pic_urls
        if article != LastArticle:
            article = LastArticle + article
        if_next = html.find('a', id='next')
        if if_next and not if_next['href'].startswith('javascript'):
            next_url = if_next['href']
            host_url = re.compile(r'http.+?people\.com\.cn').findall(article_url)[0]
            if not next_url.startswith('http'):
                next_url = host_url + next_url
            last_data['article'] = article
            last_data['pic_urls'] = pic_urls
            self.headers['User-Agent'] = random.choice(self.user_agent_list)
            res = requests.get(next_url,headers = self.headers)
            res.encoding = 'GB2312'
            html = BeautifulSoup(res.text, 'html5lib')
            this_data['html'] = html
            self.picchina(last_data, this_data)
        else:
            page_c = html.find('div', class_='page_c')
            from_msg = ''
            if page_c:
                from_tag = page_c.find('div', class_='fr')
                if not from_tag:
                    from_tag = page_c
                    from_msg = from_tag.text
                else:
                    from_msg = ''
            title_msg = pic_tag.h1.text
            editor = html.find('i', id='p_editor').text
            article = article + '\n' + editor
            item = {}
            item['title'] = title_msg
            item['article'] = article
            item['from_msg'] = from_msg
            item['article_url'] = article_url
            item['pic_urls'] = picUrlList
            item['save_path'] = save_path

            while (True):
                try:
                    #self.WriteDataQueueLock.acquire()
                    self.WriteDataQueue.put(item,timeout=1)
                    #print('put write data = {}'.format(item))
                    #self.WriteDataQueueLock.release()
                    break
                except queue.Full:
                    #self.WriteDataQueueLock.release()
                    print('WriteDataQueue is Full.')
                    time.sleep(1)
                    continue
            return

    # 中国政协新闻网
    def cppcc(self, last_data,this_data):
        pic_urls = last_data['pic_urls']
        article = last_data['article']
        html = this_data['html']
        save_path = this_data['save_path']
        article_url = this_data['article_url']
        body = html.find('font', class_='show_c')
        pic_tag = html.find('table', class_='show_p')
        edit_tag = html.find('table', class_='bianji')
        edit = edit_tag.text
        title_tag = html.find('h1')
        from_list = re.compile(r'<p class="p1">(\d+?年\d+?月\d+日.+?来源：).+?>(.+?)</a>').findall(str(html))
        if from_list:
            from_msg = from_list[0][0] + from_list[0][1]
        if not from_list:
            from_msg=''
        pic_urls += self.getPicUrls(article_url, str(pic_tag),save_path)
        article += (body.text + '\n' + edit)
        title = title_tag.text
        item = {}
        item['title'] = title
        item['article'] = article
        item['from_msg'] = from_msg
        item['article_url'] = article_url
        item['pic_urls'] = pic_urls
        item['save_path'] = save_path
        while (True):
            try:
                #self.WriteDataQueueLock.acquire()
                self.WriteDataQueue.put(item,timeout=1)
                #print('put write data = {}'.format(item))
                #self.WriteDataQueueLock.release()
                break
            except queue.Full:
                #self.WriteDataQueueLock.release()
                print('WriteDataQueue is Full.')
                time.sleep(1)
                continue
        return


    #download pictures
    def PicturesDownload(self):
        while(True):
            #print('download picture.')
            # for i in range(5):

            try:
                #self.PicturesQueueLock.acquire()
                pic_data = self.PicturesQueue.get(timeout=1)
                print(f'图片：{self.PicturesQueue.qsize()}')
                #self.PicturesQueueLock.release()
                # break
            except queue.Empty:
                #self.PicturesQueueLock.release()
                #print('PicturesQueue is Empty.')
                if_end = True
                for event in self.ArticleAnalysThreadList:
                    if event.is_alive():
                        if_end = False
                        break
                if if_end:
                    print('analys is out.pic download exit now.')
                    return
                time.sleep(5)
                continue
                    # if i>=4:
                    #     print('PicturesDownload is exit.')
                    #     return
            pic_url = pic_data['pic_url']
            save_path = pic_data['save_path']
            name = tools.cntools.StrToMD5(pic_url)+'.jpg'
            abs_path = save_path+name
            res = RequestGet(pic_url)
            if not res:
                continue
            if not os.path.exists(save_path):
                try:
                    os.makedirs(save_path)
                except:
                    tools.cntools.logger(traceback.format_exc())
            fp = open(abs_path,'wb')
            fp.write(res.content)
            fp.close()


    # 从队列取出数据，格式化存入指定目录
    def WriteData(self):
        while(True):
            # for i in range(5):
            #print('WriteData.')
            try:
                #self.WriteDataQueueLock.acquire()
                data = self.WriteDataQueue.get(timeout=1)
                print(f'写入数据：{self.WriteDataQueue.qsize()}')
                #self.WriteDataQueueLock.release()
                # break
            except queue.Empty:
                #self.WriteDataQueueLock.release()
                #print('WriteDataQueue is Empty.')
                if_end = True
                for event in self.ArticleAnalysThreadList:
                    if event.is_alive():
                        if_end = False
                        break
                if if_end:
                    print('analys is out.datawrite exit now.')
                    return
                time.sleep(5)
                continue
                    # if i >=4 :
                    #     return
            # 格式化数据
            title = data['title']
            article = data['article']
            from_msg = data['from_msg']
            article_url = data['article_url']
            pic_urls = data['pic_urls']
            save_path = data['save_path']
            obs_file = save_path+'data.csv'
            print(f'write data:{save_path}:{title},{article_url}')
            if not os.path.exists(save_path):
                try:
                    os.makedirs(save_path)
                except:
                    tools.cntools.logger(traceback.format_exc())
            if not os.path.exists(obs_file):
                first_line ='p_id,p_title,p_content,p_time,p_pictures\n'
                fp = open(obs_file,'w')
                fp.write(first_line)
                fp.close()
            f_title = tools.cntools.StrToBase64(title)
            f_article = tools.cntools.StrToBase64(article)
            f_from_msg = tools.cntools.StrToBase64(from_msg)
            for i in range(len(pic_urls)):
                pic_urls[i] = tools.cntools.StrToMD5(pic_urls[i])+'.jpg'
            f_pic_urls = str(pic_urls).replace(',','|')
            id = article_url[article_url.rfind('.cn/')+4:article_url.rfind('.')].replace('/','-')
            data_line = f'{id},{f_title},{f_article},{f_from_msg},{f_pic_urls}\n'
            with self.WriteDataLock:
                data_fp = open(obs_file,'a')
                data_fp.write(data_line)
                data_fp.close()


    #图片过滤
    def PicUrlsFilter(self,input_list):
        result = []
        for url in input_list:
            for f in self.filter_box:
                if f in url:
                    continue
                result.append(url)
        return result





    def test(self):
        main_url = self.MainUrlList[0]
        first_page = self.GetFirstPage(main_url)
        print(first_page)
        url = list(first_page.keys())[0]
        save_path = first_page[url]
        t1 = threading.Thread(target=self.GetContentUrls,args=(url,save_path))
        t2 = threading.Thread(target=self.ArticleAnalys)
        t3 = threading.Thread(target=self.WriteData)
        t4 = threading.Thread(target=self.PicturesDownload)
        t1.start()
        t2.start()
        t3.start()
        t4.start()
    def start(self):
        # 至少四线程
        # 获取文章url、文章数据解析下载、图片下载、文章格式化写入
        t_list = []
        print(self.MainUrlList)
        for main_url in self.MainUrlList:
            self.PageInIt(main_url)
        t1 = threading.Thread(target=self.GetPageThreads)
        t_list.append(t1)
        # 文章解析线程数：4
        for i in range(self.AnalyseThreads):
            print(i)
            t2 = threading.Thread(target=self.ArticleAnalys,args=(str(i),),name=str(i))
            t_list.append(t2)
            self.ArticleAnalysThreadList.append(t2)

        for i in range(self.PicDownloadThreads):
            t4 = threading.Thread(target=self.PicturesDownload)
            t_list.append(t4)
        for i in range(self.WriteDataThreads):
            t3 = threading.Thread(target=self.WriteData)
            t_list.append(t3)
        for thread in t_list:
            thread.start()
        for thread in t_list:
            thread.join()
        print('Process Exit.')
        return




def main():
    a = cnpeople()
    a.start()

if __name__ == '__main__':
    main()




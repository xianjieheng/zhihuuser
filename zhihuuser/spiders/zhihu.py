# -*- coding: utf-8 -*-
import json

import scrapy
from scrapy import Request, Spider

from zhihuuser.items import UserItem


class ZhihuSpider(Spider):

#定义爬虫名字、种子用户
    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['http://www.zhihu.com/']
    start_user = 'jjmoe'

#请求用户个人信息页，这里user可以用format函数构造字符串来传入不同用户的url_token达到构造不同用户的主页
#user_query为用户主页请求的一些附带信息，加到user_url即可实现请求用户个人信息页（这个用户信息页是知乎的接口，该接口通过ajax请求生成用户信息页，提取该页即可）
    user_url = 'https://www.zhihu.com/api/v4/members/{user}?include={include}'
    user_query = 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics'

#定义用户关注列表url，也是通过传入url_token构造用户，从而获取该用户的关注列表（这个用户列表也是通过接口ajax请求生成用户关注列表）
    follows_url = 'https://www.zhihu.com/api/v4/members/{user}/followees?include={include}&offset={offset}&limit={limit}'
    follows_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

#构造初始请求，分别抛出用户信息页和用户关机列表的请求，回调给处理用户信息页和处理用户关注列表函数
    def start_requests(self):
        yield Request(self.user_url.format(user=self.start_user,include=self.user_query),self.parse_user)
        yield Request(self.follows_url.format(user=self.start_user, include=self.follows_query,offset=0,limit=20), self.parse_follows) #这里offset为关注列表的页数导航，limit为每页大小

#处理用户信息页，抛出用户信息item给piplines储存，同时提取用户url_token构造该用户的关注列表，并执行请求，再回调给处理关注列表函数
    def parse_user(self, response):
        result = json.loads(response.text)      #获取用户信息页的信息，由于页面为json信息，所以需要用到json。loads
        item = UserItem()                       #实例化一个item类，这个类有很多fileds字段用于提取用户信息（类似CSS选择器选择对应字段之类）
        for field in item.fields:               #从item获取所有item.fields字段（也就是用户信息的字段）
            if field in result.keys():          #如果字段在用户信息结果里，则将对应用户信息字段的值传给item对应字段（抓取到对应信息）
                item[field] = result.get(field)
        yield item                              #抛出抓取到的item

        yield Request(self.follows_url.format(user=result.get('url_token'),include=self.follows_query,offset=0,limit=20),self.parse_follows)

#处理用户关注列表也，提取列表里用户的url_token，构造成新的用户信息请求，这个请求又抓取新的用户信息和抛出新的关注列表请求，实现递归抓取。并执行当前列表翻页
    def parse_follows(self, response):
        result = json.loads(response.text)

        if 'data' in result.keys():             #判断用户列表有无data字段
            for result in result.get('data'):   #遍历data里面的子字段（也就是用户列表每个用户信息）
                yield  Request(self.user_url.format(user=result.get('url_token'),include=self.user_query),self.parse_user) #抓取用户信息里的url_token，回调给处理用户信息函数，再次爬取用户信息和关注列表

        if 'paging' in result.keys() and result.get('paging').get('is_end') == False:       #通过paging里的is_end字段判断是否为最后一页
            next_page = result.get('paging').get('next')                                    #非最后一页则抓取下一页关注列表，再回调给处理列表函数，实现列表翻页
            yield  Request(next_page,self.parse_follows)

#这个爬虫要区分一个概念，
# 以往的爬虫都是：1请求初始的页面，2提取初始页面的信息，3再去获取初始页面里的链接，4再请求这些链接，提取这些链接的信息和获取新的链接进行层层爬取。这些爬虫是需要进到每个页面才能进一步获取到链接去爬取的
#这次的爬虫是：
#1请求初始用户的信息页（实际是知乎的一个接口，通过ajax请求用户信息），提取初始用户的信息，
#1请求初始用户的关注列表（也是知乎的一个接口，通过ajax请求用户列表），提取关注用户的url_token（普通爬取是直接抓取链接，这里是抓取关键字段重新构造新的请求实现递归）
#实际上是同步进行信息和关注列表的请求的
#2再从关注列表获取新的用户信息页和新的用户的关注列表 这里是直接用第一步的关注列表里直接获取关注用户的url_token去构造新的用户信息页和列表页的url再请求

#测试git
#再次测试
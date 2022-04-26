import json
import time
import random
import requests
import numpy as np
import pandas as pd
from lxml import etree
from bs4 import BeautifulSoup


class Worker(object):
    SERIES_TIMESERIES = 1
    SERIES_CROSSSECTION = 2
    SERIES_PANEL = 3
    FRAME_TIMESERIES = 4
    FRAME_CROSSSECTION = 5
    FRAME_PANEL = 6
    
    def __init__(self, data: 'pd.DataFrame | pd.Series'):
        self.data = data
        self._validate()

    def _validate(self):

        if self.data.empty:
            raise ValueError('Dataframe or Series is empty')

        is_ts = not isinstance(self.data.index, pd.MultiIndex) and isinstance(self.data.index, pd.DatetimeIndex)
        is_cs = not isinstance(self.data.index, pd.MultiIndex) and not isinstance(self.data.index, pd.DatetimeIndex)
        is_panel = isinstance(self.data.index, pd.MultiIndex) and len(self.data.index.levshape) == 2 \
                and isinstance(self.data.index.levels[0], pd.DatetimeIndex) and not isinstance(self.data.index.levels[1], pd.DatetimeIndex)
        
        if isinstance(self.data, pd.Series):
            if is_ts:
                self.type_ = Worker.SERIES_TIMESERIES
            if is_cs:
                self.type_ = Worker.SERIES_CROSSSECTION
            if is_panel:
                self.type_ = Worker.SERIES_PANEL
            else:
                raise ValueError("Your dataframe or series seems not supported in our framework")

        elif isinstance(self.data, pd.DataFrame):
            if is_ts:
                self.type_ = Worker.FRAME_TIMESERIES
            if is_cs:
                self.type_ = Worker.FRAME_CROSSSECTION
            if is_panel:
                self.type_ = Worker.FRAME_PANEL           
            else:
                raise ValueError("Your dataframe or series seems not supported in our framework")
            
    def _indexer(self, datetime, asset, indicator):
        data = self.data.copy()

        # if series, meaning there is only one indicato
        if self.type_ == Worker.SERIES_TIMESERIES:
            return data.loc[datetime]
        
        elif self.type_ == Worker.SERIES_CROSSSECTION:
            return data.loc[asset]
        
        elif self.type_ == Worker.SERIES_PANEL:
            if isinstance(datetime, str):
                return data.loc[(datetime, asset)].droplevel(0)
            if isinstance(asset, str):
                return data.loc[(datetime, asset)].droplevel(1)
        
        # if dataframe, meaning there are multiple indicatos
        elif self.type_ == Worker.FRAME_TIMESERIES:
            return data.loc[datetime, indicator]
        
        elif self.type_ == Worker.FRAME_CROSSSECTION:
            return data.loc[asset, indicator]

        elif self.type_ == Worker.FRAME_PANEL:
            if isinstance(datetime, str) and not isinstance(asset, str):
                return data.loc[(datetime, asset), indicator].droplevel(0)
            elif isinstance(asset, str):
                return data.loc[(datetime, asset), indicator].droplevel(1)
            elif isinstance(datetime, str) and isinstance(asset, str):
                res = data.loc[(datetime, asset), indicator]
                res.name = res.name[0].strftime(r'%Y-%m-%d')
            elif isinstance(indicator, str):
                return data.loc[(datetime, asset), indicator].unstack(level=1)
            else:
                raise ValueError('Unsupported indexer')

class Request(object):

    def __init__(self, url, headers: dict = None, **kwargs):
        self.url = url
        if headers:
            headers.update(self.header())
            self.headers = headers
        self.kwargs = kwargs
        
    def header(self):
        ua_list = [
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
            'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
            ]
        base_header = {
            "User-Agent": random.choice(ua_list),
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.8'
        }
        return base_header

    def get(self):
        try:
            response = requests.get(self.url, headers=self.headers, **self.kwargs)
            response.raise_for_status()        
            self.response = response
            print(f'[+] {self.url} Get Success!')
            return self
        except Exception as e:
            print(f'[-] Error: {e}')

    def post(self):
        try:
            response = requests.post(self.url, headers=self.headers, **self.kwargs)
            response.raise_for_status()        
            self.response = response
            print(f'[+] {self.url} Post Success!')
            return self
        except Exception as e:
            print(f'[-] Error: {e}')

    @property
    def etree(self):
        return etree.HTML(self.response.text)

    @property
    def json(self):
        return json.loads(self.response.text)
    
    @property
    def soup(self):
        return BeautifulSoup(self.response.text, 'lxml')

class ProxyRequest(Request):
    
    def __init__(self, url, headers: dict = None, 
        proxies: dict = None, timeout: int = None, 
        retry: int = None, retry_delay: float = None,**kwargs):
        super().__init__(url, headers, **kwargs)
        self.proxies = {} if proxies is None else proxies
        self.timeout = 2 if timeout is None else timeout
        self.retry = -1 if retry is None else retry
        self.retry_delay = 0 if retry_delay is None else retry_delay
        self.kwargs = kwargs
    
    def get(self):
        if isinstance(self.proxies, dict):
            self.proxies = [self.proxies]
        random.shuffle(self.proxies) 
        if self.retry == -1:
            self.retry = len(self.proxies)
        for try_times, proxy in enumerate(self.proxies):
            if try_times + 1 <= self.retry:
                try:
                    response = requests.get(self.url, headers=self.headers, proxies=proxy, **self.kwargs)
                    response.raise_for_status()
                    self.response = response
                    print(f'[+] {self.url}, try {try_times + 1}/{self.retry}')
                    return self
                except Exception as e:
                    print(f'[-] [{e}] {self.url}, try {try_times + 1}/{self.retry}')
                    time.sleep(self.retry_delay)

    def post(self):
        if isinstance(self.proxies, dict):
            self.proxies = [self.proxies]
        random.shuffle(self.proxies) 
        if self.retry == -1:
            self.retry = len(self.proxies)
        for try_times, proxy in enumerate(self.proxies):
            if try_times + 1 <= self.retry:
                try:
                    response = requests.post(self.url, headers=self.headers, proxies=proxy, **self.kwargs)
                    response.raise_for_status()
                    self.response = response
                    print(f'[+] {self.url}, try {try_times + 1}/{self.retry}')
                    return self
                except Exception as e:
                    print(f'[-] [{e}] {self.url}, try {try_times + 1}/{self.retry}')
                    time.sleep(self.retry_delay)

    def get_async(self, container: dict):
        if isinstance(self.proxies, dict):
            self.proxies = [self.proxies]
        random.shuffle(self.proxies) 
        if self.retry == -1:
            self.retry = len(self.proxies)
        for try_times, proxy in enumerate(self.proxies):
            if try_times + 1 <= self.retry:
                try:
                    response = requests.get(self.url, headers=self.headers, proxies=proxy, **self.kwargs)
                    response.raise_for_status()
                    self.response = response
                    container[self.url] = self.process()
                    print(f'[+] {self.url}, try {try_times + 1}/{self.retry}')
                    break
                except Exception as e:
                    print(f'[-] [{e}] {self.url}, try {try_times + 1}/{self.retry}')
                    time.sleep(self.retry_delay)

    def post_async(self, container: dict):
        if isinstance(self.proxies, dict):
            self.proxies = [self.proxies]
        random.shuffle(self.proxies) 
        if self.retry == -1:
            self.retry = len(self.proxies)
        for try_times, proxy in enumerate(self.proxies):
            if try_times + 1 <= self.retry:
                try:
                    response = requests.post(self.url, headers=self.headers, proxies=proxy, **self.kwargs)
                    response.raise_for_status()
                    self.response = response
                    container[self.url] = self.process()
                    print(f'[+] {self.url}, try {try_times + 1}/{self.retry}')
                    break
                except Exception as e:
                    print(f'[-] [{e}] {self.url}, try {try_times + 1}/{self.retry}')
                    time.sleep(self.retry_delay)

    def process(self):
        raise NotImplementedError

if __name__ == "__main__":
    pass
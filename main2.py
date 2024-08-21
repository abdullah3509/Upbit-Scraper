#!/usr/bin/python3
import json
import requests
import random
from bs4 import *
from discord_hooks import Webhook
import threading
import time
from datetime import datetime
from random import randint

def send_embed(code,title):

    global _config
    date_str = str(datetime.now()) 

  
    time = str(datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f'))
    embed = Webhook(_config["webhook"], color="16711680")
    link = "https://upbit.com/service_center/notice?id="+code
    embed.set_title(title=str(title), url=link)
    embed.add_field(name='Timestamp',value=time)
    embed.set_footer(text="to be changed by client request 2", ts=True)
    embed.post()

def read_config():
    f = open("config.json","r")
    config = json.loads(f.read())
    f.close()
    return config

def load_proxies():

    f = open("proxies.txt", "r")
    proxy_list = f.readlines()
    f.close()
    return proxy_list

def WriteDatabase():
    while True:
        global db
        #Write new database
        with open("db.json", "w") as f:
            f.write(json.dumps(db, indent=4, sort_keys=True))
            f.close()
        time.sleep(45)

def get_random_proxy():

    global _proxies

    proxy = random.choice(_proxies).strip()

    try:
        proxyform = proxy.split(":")
        proxy = proxyform[2].strip() + ":" + proxyform[3].strip() + "@" + proxyform[0].strip() + ":" + proxyform[1].strip()
    except:
        pass

    proxies = {"http": "http://{}".format(proxy), "https": "http://{}".format(proxy)}
    return proxies

def make_request(url):

    global _headers, AGENTS, _s
    try:
        proxies = get_random_proxy()
        
        headers = {
          'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'upgrade-insecure-requests': '1',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
          'sec-fetch-site': 'cross-site',
          'sec-fetch-mode': 'navigate',
          'sec-fetch-user': '?1',
          'sec-fetch-dest': 'document',
          'accept-encoding': 'gzip, deflate, br, zstd',
          'accept-language': f'ko-KR, ko;q=1, it-IT;q=0.1 {str(random.randint(1,5000000))}',
        }
        
        # query=      '-'+str(random.randint(2,999999999999990))+'&per_page=20&category=all&os=web&-' +str(random.randint(1,999999999999999))

        # urluncached = url +query
        cache_buster = str(random.randint(100000, 999999))
        # Append the cache buster parameter to the URL
        urluncached = f"{url}&cb={cache_buster}"

        r = requests.get(urluncached,headers=headers,timeout=3)
        print(r.status_code)
        


        if(r.status_code == 200):
            print(r.headers['cf-cache-status'])
            print(datetime.now().strftime("[%H:%M:%S]") + "[OK]"+ urluncached)
            try:
                "a" in r.text
                if r.text is not None and r is not None:
                    return r
                else:
                    return None
            except:
                return None
        else:
            print(datetime.now().strftime("[%H:%M:%S]") + "[BAD]"+ urluncached)
            return None
    except Exception as e:
        print(e)
        return None

def find_message(link1):
    global db

    while True:
        try:
            r = make_request(link1)
            if r is not None:
                if r.text.startswith('{'):              
                    data = r.json()
                    for message in data['data']['notices']:
                        code = str(message['id'])
                        title = message['title']

                        if code not in db:
                            db[code] = {
                                "Title": title,
                              }
                            send_embed(code, title)
                            with open("db.json", "w", encoding='utf-8') as f:
                                json.dump(db, f, indent=4, sort_keys=True, ensure_ascii=False)
                        else:
                            pass
                else:            
                    print("An error occurred: Not JSON Payload...")
            
        except Exception as e:
            print(e)

def main():

    global _config, db
    url1 = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=10&category=all'
    for a in range(10):
        threading.Thread(target = find_message, args=(url1,)).start()
        time.sleep(0.1)

     
if __name__ == "__main__":

    print(datetime.now().strftime("[%H:%M:%S]") + "Loading data...")

    #Gets database
    requests.packages.urllib3.disable_warnings()
    f = open("db.json", "r",encoding='utf-8')
    db = json.loads(f.read())
    f.close()

    #Loads config file
    _config = read_config()

    #Loads proxies
    _proxies = load_proxies()


    threading.Thread(target = WriteDatabase).start()

    _s = requests.Session()

    main()

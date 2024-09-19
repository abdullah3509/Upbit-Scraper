#!/usr/bin/python3
import json
import requests
import threading
import time
from discord_hooks import Webhook
from collections import defaultdict
from datetime import datetime , timedelta
import logging
import random
import uuid

requests.packages.urllib3.disable_warnings()

# Global variables
logging.basicConfig(filename = f"logs.log",
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

proxy_request_times = defaultdict(list)
stop_event = threading.Event()

def send_embed(code, time_str,title):
    global _config

    embed = Webhook(_config["webhook"], color=16711680)
    link = f"https://upbit.com/service_center/notice?id={code}"
    embed.set_title(title=title, url=link)
    embed.add_field(name='Timestamp', value=time_str)
    embed.set_footer(text="to be changed by client request 2", ts=True)
    embed.post()
    message_ = time_str + " [NEW NOTICE FOUND] " + str(code)
    print(message_)
    logging.info(" [NEW NOTICE SENT] " + str(code))

def printError(e):
    import sys
    error_type = type(e).__name__
    line_number = sys.exc_info()[-1].tb_lineno
    if e.args:
        error_name = e.args[0]
    else:
        error_name = "No additional information available"
    error_msg = f"Error Type: {error_type}\nError Name: {error_name}\nLine where error occurred: {line_number}"
    print(error_msg)

def read_config():
    with open("config.json", "r") as f:
        return json.load(f)

def load_proxies():
    with open("proxies_D.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

def write_database():
    while True:
        global db
        with open("db.json", "w") as f:
            json.dump(db, f, indent=4, sort_keys=True)
        time.sleep(45)

def get_random_proxy():
    global _proxies

    proxy = random.choice(_proxies).strip()

    try:
        proxy_parts = proxy.split(":")
        if len(proxy_parts) == 4:
            username, password, ip, port = proxy_parts[2], proxy_parts[3], proxy_parts[0], proxy_parts[1]
            proxy_auth = f"{username}:{password}@{ip}:{port}"
            proxies = {
                "http": f"http://{proxy_auth}",
                "https": f"http://{proxy_auth}"
            }
            return proxies
    except Exception as e:
        print(f"Failed to parse proxy {proxy}: {e}")
        return None

def rate_limit(proxy):
    current_time = time.time()
    # Keep only the timestamps within the last second
    proxy_request_times[proxy] = [t for t in proxy_request_times[proxy] if t > current_time - 1]

    if len(proxy_request_times[proxy]) >= 5:
        sleep_time = 1 - (current_time - proxy_request_times[proxy][0])
        if sleep_time > 0:
            time.sleep(sleep_time)
        proxy_request_times[proxy] = proxy_request_times[proxy][1:]  # Remove the oldest timestamp

    proxy_request_times[proxy].append(time.time())
    
def make_request(url):
    global proxy_request_times, _s

    headers = {
    'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-dest': 'document',
    'accept-language': f'ko-KR, ko;q=1, it-IT;q=0.1 {str(random.randint(1,5000000))}',
    }

    try:
        proxies = get_random_proxy()
    
        cache_buster = str(uuid.uuid4())
        url_uncached = f"{url}&cb={cache_buster}"

        # Rate limiting logic
        if proxies:
            rate_limit(proxies['http'])
        
        if proxies is None:
            print("No valid proxy available, skipping proxy for this request.")
            r = _s.get(url_uncached, headers=headers, timeout=3)
        else:
            r = _s.get(url_uncached, headers=headers, proxies=proxies, timeout=3)

        if r.status_code == 200:
            print(r.headers.get('cf-cache-status', 'No cache status'))
            print(datetime.now().strftime("[%H:%M:%S]") + "[OK] " + url_uncached)
            if r.text is not None and r:
                return r
        else:
            print(datetime.now().strftime("[%H:%M:%S]") + "[BAD] " + url_uncached)
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def find_message(url):
    global db
    while not stop_event.is_set():
        start_time = datetime.now()
        time.sleep(0.3)
        r = make_request(url)
        if r is None:
            continue
        elif r.text.startswith('{'):
            try:
                data = r.json()
                for message in data['data']['notices']:
                    code = str(message['id'])
                    title = message['title']
                    if code not in db:
                        db[code] = {"Title": title}
                        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        send_embed(code,time_str, title)
                        end_time = datetime.now()
                        elapsed_time = (end_time - start_time).total_seconds() * 1000
                        logging.info(f"Total time taken by the bot: {elapsed_time}-ms.")

                        with open("db.json", "w", encoding='utf-8') as f:
                            json.dump(db, f, indent=4, sort_keys=True, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
            except Exception as e:
                print(f"Error processing response: {e}")
        else:
            print("Rate limit for the proxy exceeded. Temporary banned IP from UPBIT.")
        


def main():
    global _config, db, _headers, _s

    try:
        _s = requests.Session()
                   
        base_url = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=all'
        print("Script started. Press Ctrl + C to stop.")

        threads = []
        for _ in range(2):
            thread = threading.Thread(target=find_message, args=(base_url,))
            thread.start()
            threads.append(thread)
            time.sleep(0.1)

        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nScript terminated by user (Ctrl + C).")
        stop_event.set()
        for thread in threads:
            thread.join()
        exit()

if __name__ == "__main__":
    print(datetime.now().strftime("[%H:%M:%S]") + "Loading data...")

    # Load database
    with open("db.json", "r",encoding='utf-8') as f:
        db = json.load(f)

    # Load config and proxies
    _config = read_config()
    _proxies = load_proxies()

    # Start writing to the database periodically
    threading.Thread(target=write_database).start()

    main()
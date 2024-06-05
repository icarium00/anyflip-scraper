import requests
import re
from PIL import Image
from io import BytesIO
from progress.bar import Bar
import sys
from threading import Thread,Lock
import os
import random
from fake_useragent import UserAgent

ua = UserAgent()

url = sys.argv[1]
if len(sys.argv) >= 2:
    title = sys.argv[2]
elif len(sys.argv == 1):
    title = "Book"
else:
    exit("missing arguments")

header = {"User-Agent": ua.random}

def get_config(url:str) -> str:
    url = url + "/mobile/javascript/config.js"

    response = requests.get(url, headers=header)

    return response.content.decode()

def get_page_count(config:str) -> int:
    page_count = re.search('(bookConfig.)?(total)?[Pp]ageCount"?[=:]"?\d{1,5}"?', config)
    if page_count == None: return -1
    return int(re.split("[=|:]",page_count.group(0))[1].replace("\"",""))


def get_pages(config: str) -> list[str]:
    #parsing
    pages = re.findall('"n":\[".*?"\]', config)
    for i in range(len(pages)):
        pages[i] = pages[i][6:-2]

    return pages

def download_page(url:str, idx:int, book:list, mtx:Lock) -> None:
    img = requests.get(url,headers=header).content
    mtx.acquire()
    book.append((idx,img))
    mtx.release()


def download(url:str) -> None:
    element = url.split(".com")
    url = "https://online.anyflip.com" + element[1]


    config = get_config(url)
    page_count = get_page_count(config)
    data = get_pages(config)

    book = []
    threads = []
    mtx = Lock()
    with Bar("Downloading Pages") as bar:
        if data != []:
            bar.max = len(data)
            url = url + "/files/large/"
            for page in range(len(data)):
                threads.append(Thread(target=download_page, args=(url+data[page], page, book, mtx)))
                threads[-1].start()
                bar.next()
        elif page_count != -1:
            bar.max = page_count
            url = url + "/files/mobile/"
            for page in range(1,page_count+1):
                threads.append(Thread(target=download_page, args=(url+str(page)+".jpg", page-1, book, mtx)))
                threads[-1].start()
                bar.next()
        else:
            print("\nError")
            return
    for t in threads:
        t.join()
    bar.finish()
    
    book.sort()

    pdf_path = os.getcwd() + "/" + title + ".pdf"

    with Bar("Creating PDF", max=2) as bar:
        images = [
            Image.open(BytesIO(i[1]))
            for i in book
        ]
        bar.next()
        
        images[0].save(
            pdf_path, "PDF" ,resolution=100.0, save_all=True, append_images=images[1:]
        )
        bar.next()
    bar.finish()

download(url)

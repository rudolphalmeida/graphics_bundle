__version__ = "0.1.0"

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


import os
import sys
import time
import asyncio
import threading
import itertools

import aiohttp
import aiofiles


class Spinner:
    """
    Spinner class representing a spinner that runs in a separate thread
    This class supports displaying a message (`msg`)
    and an exit message (`exit_msg`) and also custom spinner styles by
    settings a list or string of values for `states` in the constructor

    Usage:
    spinner = Spinner("Message to display while spinning")
    spinner.start()
    spinner.stop("Message to display after spinner is stopped")  # Stop spinner
    """

    def __init__(self, msg, states=None):
        if states is None:
            states = ["[=  ]", "[ = ]", "[  =]", "[ = ]"]

        self.states = states
        self.msg = msg
        self.exit_msg = None
        self.spinner = None
        self.done = threading.Event()  # Conditional Variable to signal stop

    def start(self):
        if self.spinner is not None:
            raise Exception("Cannot call start on an already started Spinner")
        self.spinner = threading.Thread(target=Spinner.spin, args=(self,))
        self.spinner.start()  # Start spinner in new thread

    def spin(self):
        write, flush = sys.stdout.write, sys.stdout.flush
        prompt = ""
        for state in itertools.cycle(self.states):
            prompt = "{} {}".format(state, self.msg)
            write(prompt)  # Write state and message
            flush()
            write("\b" * len(prompt))  # Move cursor back to start
            if self.done.wait(0.1):
                break
        # Write exit message after clearing old prompt
        write(
            " " * len(prompt) + "\b" * len(prompt) + self.exit_msg
            if self.exit_msg
            else ""
        )
        flush()

    def stop(self, exit_msg):
        self.exit_msg = exit_msg
        self.done.set()  # Set conditional variable...
        self.spinner.join()  # ...and wait for thread to exit


def find_chapters(driver):
    # Find all chapters links on the Chapters tab of a book
    elements = driver.find_elements_by_xpath(
        "//tr[contains(@class, 'matter-type-chapter')]/td[2]/span[@class='cdp-organizer-chapter-title']/span/a"
    )

    if elements:
        return elements
    else:
        return False


def find_images(driver):
    # Find all images in chapter
    # img tags can be inside a div or a p tag
    # We use the src attribute of the img
    # tag to determine images. All non-CDP images which are inside content
    # have `upload` in their URL
    try:
        elements = [
            element.get_attribute("src")
            for element in driver.find_elements_by_xpath(
                ("//img[contains(@src, 'upload')]")
            )
        ]
    except StaleElementReferenceException:
        # Found a stale reference. We wait for some time (5s) and try again
        time.sleep(5)
        elements = [
            element.get_attribute("src")
            for element in driver.find_elements_by_xpath(
                ("//img[contains(@src, 'upload')]")
            )
        ]

    if elements:
        return elements
    else:
        return False


async def download_and_save_image(image_no, url, book_code, chap_no):
    async with aiohttp.ClientSession() as session:
        print("Downloading {} from {}".format(image_no, chap_no))
        async with session.get(url) as response:
            print("Downloaded {} from {}".format(image_no, chap_no))
            if response.status == 200:
                ext = url.split(".")[-1].split("?")[0]
                f = await aiofiles.open(
                    "{book_code}\\Chapter {chap_no}\\{book_code}_{chap_no}_{image_no}.{ext}".format(
                        image_no=image_no, book_code=book_code, chap_no=chap_no, ext=ext
                    ),
                    mode="wb",
                )
                await f.write(await response.read())
                await f.close()


async def process_chapter(driver, book_code, chap_no):
    os.makedirs("{}\\Chapter {}".format(book_code, chap_no))

    # Switch to content frame
    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "content_ifr")))
    except TimeoutException:
        print("Failed to find `content_ifr` frame. Are we on the right page?")
        driver.close()
        sys.exit(-1)

    # Find all images in a chapter. We wait for a maximum of 10s
    # to allow CDP to load. If after that no images are found we assume
    # that the chapter has no images in it
    try:
        images = WebDriverWait(driver, 10).until(find_images)
    except TimeoutException:
        # The chapter *might* have no images
        print("----Found no images in Chapter #{}".format(chap_no))
        return ""

    tasks = []
    for image_no, url in enumerate(images):
        tasks.append(download_and_save_image(image_no, url, book_code, chap_no))

    await asyncio.gather(*tasks)

    driver.switch_to.default_content()  # Switch to main chapter page


def main():
    print("Welcome to Image Downloader for Packt...")
    book_code = input("Please enter the book code of the book: ")
    os.makedirs(book_code)
    print("I need the URL of the book")
    print("Please enter the Chapter list URL for your book")
    book_url = input("URL> ")

    options = webdriver.ChromeOptions()
    # Use selenium directory to load cookies and state for Chrome
    # This will ensure that once logged-in the user does not has to
    # log-in for a while
    options.add_argument("user-data-dir=selenium")

    # Start new Chrome instance
    driver = webdriver.Chrome(options=options)
    driver.get(book_url)

    print("Unfortunately I am a robot and cannot login :(")
    print("I need you to login for me so I can do my work")
    print("If you are already logged in, just press Enter")
    print("Press Enter when you are done...")

    input("")  # Wait for user to login

    chapters = WebDriverWait(driver, 3).until(find_chapters)

    for chap_no in range(1, len(chapters) + 1):
        spinner = Spinner("Processing Chapter #{}".format(chap_no))

        # We need to load the chapter list every time the page is opened
        chapter = WebDriverWait(driver, 3).until(find_chapters)[chap_no - 1]

        driver.get(chapter.get_attribute("href"))  # Visit chapter

        spinner.start()

        # process each chapter...
        asyncio.run(process_chapter(driver, book_code, chap_no))

        spinner.stop("Chapter #{} done...\n".format(chap_no))

        driver.get(book_url)  # ...and go back to chapter list

    driver.close()  # Close Chrome window

    print("Images written to {book_code} folder...".format(book_code=book_code))


if __name__ == "__main__":
    main()

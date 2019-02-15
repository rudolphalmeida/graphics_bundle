__version__ = "0.1.0"

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import sys
import time
import threading
import itertools
from html.parser import HTMLParser

CHAPTER_HEADER = '<h1 class="mce-root CDPAlignLeft CDPAlign">Chapter {no}: {name}</h1>'
IMAGE_TEMPLATE = '<p class="CDPAlignCenter CDPAlign">{img_tag}</p>'


class Spinner:
    """
    Spinner class representing a `spinner` that runs in a seperate thread
    This class supports displaying a message (msg) and an exit message (`exit_msg`)
    """

    def __init__(self, msg, states=None):
        if states is None:
            states = ["[=  ]", "[ = ]", "[  =]", "[ = ]"]

        self.states = states
        self.msg = msg
        self.done = threading.Event()  # Conditional Variable

    def start(self, exit_msg):
        self.spinner = threading.Thread(target=Spinner.spin, args=(self, exit_msg))
        self.spinner.start()  # Start spinner in new thread

    def spin(self, exit_msg):
        write, flush = sys.stdout.write, sys.stdout.flush
        for state in itertools.cycle(self.states):
            prompt = "{} {}".format(state, self.msg)
            write(prompt)  # Write state and message
            flush()
            write("\b" * len(prompt))  # Move cursor back to start
            if self.done.wait(0.1):
                break
        # Write exit message after clearing old prompt
        write(" " * len(prompt) + "\b" * len(prompt) + exit_msg)
        flush()

    def stop(self):
        self.done.set()  # Set conditional variable...
        self.spinner.join()  # ...and wait for thread to exit


class IgnoreWidthHeightParser(HTMLParser):
    """
    HTMLParser subclass to parse a single tag and remove the `width` and
    `height` attributes of the tag
    """

    def __init__(self, *args, **kwargs):
        self.attributes = ""  # str to hold useful attributes
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if attr not in ("width", "height"):
                self.attributes += ' {}="{}" '.format(attr, value)


def strip_img_width_height(tag):
    """
    Strip the `width` and `height` attribute of a single HTML img tag using
    `IgnoreWidthHeightParser`
    """
    parser = IgnoreWidthHeightParser()
    parser.feed(tag)  # Feed data to the parser
    parser.close()
    return "<img {}>".format(parser.attributes)  # Recreate HTML tag


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
    # We could use @class=CDPAlignCenter to find the exact div and p's
    # But if someone has missed centering an image that img will not be
    # included in the GC. As a result we use the src attribute of the img
    # tag to determine images. All non-CDP images which are inside content
    # have `upload` in their URL
    try:
        elements = [
            strip_img_width_height(element.get_attribute("outerHTML"))
            for element in driver.find_elements_by_xpath(
                (
                    "//div/img[contains(@src, 'upload')] |"  # img in div
                    "//p/img[contains(@src, 'upload')] |"  # img in paragraph
                    "//td/img[contains(@src, 'upload')]"  # img in table
                )
            )
        ]
    except StaleElementReferenceException:
        # Found a stale reference. We wait for some time (5s) and try again
        time.sleep(5)
        elements = [
            strip_img_width_height(element.get_attribute("outerHTML"))
            for element in driver.find_elements_by_xpath(
                (
                    "//div/img[contains(@src, 'upload')] |"
                    "//p/img[contains(@src, 'upload')] |"
                    "//td/img[contains(@src, 'upload')]"
                )
            )
        ]

    if elements:
        return elements
    else:
        return False


def process_chapter(driver, chap_no):
    # Get chapter name stored in `value` of the `post_title` input
    chapter_name = driver.find_element_by_name("post_title").get_attribute("value")

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

    # Format chapter header using chapter name
    chapter_gb_source = CHAPTER_HEADER.format(no=chap_no, name=chapter_name)

    # Append images to GB
    for image in images:
        chapter_gb_source += IMAGE_TEMPLATE.format(
            img_tag=image
        )  # Get img html source and append to GB source

    chapter_gb_source += "<pagebreak/>"

    driver.switch_to.default_content()  # Switch to main chapter page

    return chapter_gb_source


def main():
    print("Welcome to Graphics Bundle Creator for Packt...")
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

    book_gb_source = ""

    for chap_no in range(1, len(chapters) + 1):
        spinner = Spinner("Processing Chapter #{}".format(chap_no))

        # We need to load the chapter list every time the page is opened
        chapter = WebDriverWait(driver, 3).until(find_chapters)[chap_no - 1]

        driver.get(chapter.get_attribute("href"))  # Visit chapter

        # process each chapter...
        spinner.start("Chapter #{} done...\n".format(chap_no))
        book_gb_source += process_chapter(driver, chap_no)
        spinner.stop()

        driver.get(book_url)  # ...and go back to chapter list

    driver.close()  # Close Chrome window

    # Required text at end of content so that CDP does not chop the last
    # chapter off
    book_gb_source += "<p>Graphics Bundle Ends Here</p>"

    print("Writing your graphics bundle to output.html...")
    with open("output.html", "w") as gb:
        gb.write(book_gb_source)


if __name__ == "__main__":
    main()

__version__ = "0.1.0"

from selenium import webdriver

CHAPTER_HEADER = '<h1 class="mce-root CDPAlignLeft CDPAlign">Chapter {no}: {name}</h1>'
IMAGE_TEMPLATE = '<p class="CDPAlignCenter CDPAlign">{img_tag}</p>'


def process_chapter(driver, chap_no):
    print("Processing Chapter #{}".format(chap_no))

    # Get chapter name stored in `value` of the `post_title` input
    chapter_name = driver.find_element_by_name("post_title").get_attribute(
        "value")

    driver.switch_to_frame("content_ifr")  # Switch to content frame

    # Find all images in chapter
    # img tags can be inside a div or a p tag
    # We could use @class=CDPAlignCenter to find the exact div and p's
    # But if someone has missed centering an image that img will not be
    # included in the GC. As a result we use the src attribute of the img
    # tag to determine images. All non-CDP images which are inside content
    # have `upload` in their URL
    images = driver.find_elements_by_xpath(
        "//div/img[contains(@src, 'upload')] | //p/img[contains(@src, 'upload')]"
    )

    # Format chapter header using chapter name
    chapter_gb_source = CHAPTER_HEADER.format(no=chap_no, name=chapter_name)

    # Append images to GB
    for image in images:
        chapter_gb_source += IMAGE_TEMPLATE.format(
            img_tag=image.get_attribute(
                "outerHTML"))  # Get img html source and append to GB source

    chapter_gb_source += "<pagebreak/>"

    driver.switch_to_default_content()  # Switch to main chapter page

    return chapter_gb_source


def main():
    print("Welcome to Graphics Bundle Creator for Packt...")
    print("I need the URL of the book")
    print("Please enter the Chapter list URL for your book")
    book_url = input("URL> ")

    # Start new Chrome instance
    # TODO: Support Firefox as well
    driver = webdriver.Chrome()
    driver.get(book_url)

    print("Unfortunately I am a robot and cannot login :(")
    print("I need you to login for me so I can do my work ;)")
    print("Press Enter when you are done...")

    input("")  # Wait for user to login

    chapters = driver.find_elements_by_xpath(
        "//span[@class='cdp-organizer-chapter-title']/span/a")

    book_gb_source = ""

    for chap_no in range(1, len(chapters) + 1):
        # We need to load the chapter list every time the page is opened
        chapter = driver.find_elements_by_xpath(
            "//span[@class='cdp-organizer-chapter-title']/span/a")[chap_no - 1]

        driver.get(chapter.get_attribute("href"))  # Visit chapter

        # process each chapter...
        book_gb_source += process_chapter(driver, chap_no)

        driver.get(book_url)  # ...and go back to chapter list

    # Required text at end of content so that CDP does not chop the last
    # chapter off
    book_gb_source += "<p>Graphics Bundle Ends Here</p>"

    print("Writing your graphics bundle to output.html...")
    with open("output.html", "w") as gb:
        gb.write(book_gb_source)


if __name__ == "__main__":
    main()

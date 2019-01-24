Graphics Bundle Creator for Packt
=================================

`graphics_bundle.py` is a solution to automate the boring job of making a graphics bundle for Packt books.

How to use
----------

1. Clone the repository to folder you want using:

        git clone https://github.com/rudolphalmeida/graphics_bundle

2. The only dependency for the script is Python 3 and Selenium. Selenium can be installed using the following command:

        pip install selenium

3. The script can then be run using:

        python graphics_bundle.py

Note
----

+ I recommend using the `git clone` command to clone the repo instead of downloading the `.zip` file. That way you can easily update to the latest version using just a `git pull` command.

+ The code assumes that chapters are arranged in the final order.

+ Please do not interact with the new Google Chrome instance opened by the script.

+ The source for the graphics bundle will be written to a file called `output.html`.

+ After copying the contents of `output.html` to the book on CDP, please go through the bundle once to check for any unnecessary images or other errors.

+ There is some final text after the last chapter to avoid the last chapter from getting chopped off by CDP so make sure you ignore that page while creating the final PDF file.

+ The program includes formula images in the graphics bundle too. If your book had some you will have to manually remove them.

+ Slow internet or slow loading because of CDP can sometimes cause the program to fail. If you see any sort of `StaleElementReferenceException` in the error, then simply try running the script again.
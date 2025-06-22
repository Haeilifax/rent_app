# TODO

-[] Make most basic test to determine feasibility (GET request to /stylesheet)
    -[] Write the basic GET test
        -[] Create unittest for GET /stylesheet.css (should return a css file)
-[] Create initial unit test of POST request functionality with testing framework
-[] Create unittest for GET / (should return an HTML file)
-[] Add GNU Terry Pratchett header
-[] Refactor main method to not be a giant, undifferentiated pile of code. Break GET and POST request handlers out.
-[] Make response function to build success and error responses without manually building a gross dict
-[] Set up environment variables in our test code before we import the rent_app package to use ISLOCAL
-[] Set up our database as a fixture
-[] Import the rent_app package in our test code
-[] Create a test function that runs lambda_handler with an event w/ method=GET and path=/stylesheet
-[] Update to only reach out to S3 if explicitly told we're not running locally

# Completed
-[X] Update our code to use resource imports for the templates and stylesheets
-[X] Update ISLOCAL to take a db location (which can also be `:memory:` for easy testing)


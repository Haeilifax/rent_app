# TODO

-[] Determine the correct .gitignore ignores for terraform
-[] Update .gitignore with only appropriate terraform ignores
-[] Manually test POST requests
    -[] Pay attention to innapropriate lease_id types?
    -[] Does the data pushed by the POST request create the right db entry?
    -[] Does the db save correctly to S3 (persistence)?
    -[] Does the UI push the correct data?
-[] Create initial unit test of POST request functionality with testing framework
-[] Create unittest for GET / (should return an HTML file)
-[] Add GNU Terry Pratchett header
-[] Refactor main method to not be a giant, undifferentiated pile of code. Break GET and POST request handlers out.
-[] Make response function to build success and error responses without manually building a gross dict
-[] Update to only reach out to S3 if explicitly told we're not running locally
-[] Add text to CLAUDE.md telling Claude not to update any file in the tests directory
-[] Start interpreting None as 0 for Amounts

# Completed
-[X] Update our code to use resource imports for the templates and stylesheets
-[X] Update ISLOCAL to take a db location (which can also be `:memory:` for easy testing)
-[X] Make most basic test to determine feasibility (GET request to /stylesheet)
    -[X] Write the basic GET test
        -[X] Create unittest for GET /stylesheet.css (should return a css file)
-[X] Set up environment variables in our test code before we import the rent_app package to use ISLOCAL
-[X] Set up our database as a fixture
-[X] Import the rent_app package in our test code
-[X] Create a test function that runs lambda_handler with an event w/ method=GET and path=/stylesheet


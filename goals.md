# TODO

-[] Add GNU Terry Pratchett header
-[] Refactor main method to not be a giant, undifferentiated pile of code. Break GET and POST request handlers out.
-[] Make response function to build success and error responses without manually building a gross dict
-[] Update to only reach out to S3 if explicitly told we're not running locally
-[] Add text to CLAUDE.md telling Claude not to update any file in the tests directory
-[] Allow month selection in UI (entails also making it dyanmically passable)
-[] Add month name to top
-[] Add ability to see each rent collection record
-[] Add real-world tenants to DB
-[] Test on mobile
-[] Make any changes needed for mobile

# Completed
-[X] Start interpreting None as 0 for Amounts
-[X] Update our code to use resource imports for the templates and stylesheets
-[X] Update ISLOCAL to take a db location (which can also be `:memory:` for easy testing)
-[X] Make most basic test to determine feasibility (GET request to /stylesheet)
    -[X] Write the basic GET test
        -[X] Create unittest for GET /stylesheet.css (should return a css file)
-[X] Set up environment variables in our test code before we import the rent_app package to use ISLOCAL
-[X] Set up our database as a fixture
-[X] Import the rent_app package in our test code
-[X] Create a test function that runs lambda_handler with an event w/ method=GET and path=/stylesheet
-[X] Determine the correct .gitignore ignores for terraform
-[X] Update .gitignore with only appropriate terraform ignores
-[X] Manually test POST requests
    -[X] Pay attention to innapropriate lease_id types?
    -[X] Does the data pushed by the POST request create the right db entry?
    -[X] Does the db save correctly to S3 (persistence)?
    -[X] Does the UI push the correct data?
-[X] Create initial unit test of POST request functionality with testing framework
-[X] Create unittest for GET / (should return an HTML file)

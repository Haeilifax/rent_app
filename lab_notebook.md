# Lab Notebook

(This is intended to be an append only description of current thoughts, attempted moves, and where I've gone with this project. Any and all information written here may be factually incorrect, and will hopefully be corrected later in the note if it is. See https://hamatti.org/posts/how-i-take-work-notes-as-a-developer/ for further details about the goal of this note)

## 2025-06-10

- We have begun using Claude Code for this project to test it out
- Initial commit forthcoming -- at the end of last session we determined what terraform files to add to .gitignore
- Current status of project is:
    - GET requests function
    - Webpage aesthetics are in the process of being improved
    - POST requests for adding CollectedRents are the next big goal
    - Experimentation with LLM Agents and code generation in general is an additional overarching goal, and may steal focus from the direct improvements of the product (for the currently more important goal of self-improvement and exploration)

- Goals for today:
    -[X] Commit everything currently in repo as appropriate
    -[] Use vanilla.css to improve the aesthetic of the webpage and have this display appropriately from the lambda function

- First thing to check is whether opening the returned html locally gives us the appropriate vanilla.css -- the initial attempt we made to apply the css should have worked, but it's not showing from the function URL
    - Is this due to some oddity of Lambda permissioning? Since it's not a server, does including the css file as a relative import fail?
    - One difficulty I have with this is that my task runner (`poe`) doesn't source the command directly in my shell, and as such I can't use it to spin up my dev shell
        - This is counter to the process I'm used to from my last job, where we used `npm` as our task runner -- I would set up a shell command to spin up an IPython process with appropriate environment variables, appropriate imports, and and initial setup that I would need in order to just start working.
        - I've done some research previously and I don't think that I have the correct keywords to be able to ask the right questions
        - I'm going to check the poe docs again, to see if there's an option or command that I can use to have it hand control over to me after finishing running, instead of just erroring out when input is allowed
            - https://poethepoet.natn.io/
            - It seems that the `use_exec` option may be the key?
                - > Normally tasks are executed as subprocesses of the poe executable. This makes it possible for poe to run multiple tasks, for example within a sequence task or task graph.
                > However in certain situations it can be desirable to define a task that is instead executed within the same process via an exec call. cmd tasks and script tasks tasks can be configured to work this way using the use_exec option like so:
                > ```[tool.poe.tasks.serve]
                    cmd      = "gunicorn ./my_app:run"
                    use_exec = true```
            - use_exec can only be used on cmd and script tasks -- I'm using a shell task currently, can I change to a cmd task?
                - difference between the two:
                    - shell task:
                        > Shell tasks are similar to simple command tasks except that they are executed inside a new shell, and can consist of multiple statements. This means they can leverage the full syntax of the shell interpreter such as command substitution, pipes, background processes, etc.
                    - cmd task:
                        > Command tasks contain a single command that will be executed as a sub-process without a shell. This covers most basic use cases such as the following examples.
                    - cmd tasks are more basic, and only shell-like -- they don't have a real bash shell, it's just poe running things in ways that in some respects look like a shell. So, running IPython is a maybe?
            - Trying to use a cmd task instead (by just changing `shell` to `cmd`) fails because it thinks that me setting environment variables is supposed to be the task. I wonder if we can just eliminate those and spawn the shell (if we need to set them, we could just do it from IPython)
            - Beaut, that worked -- IPython started right up. We're in business!
        - Okay, so testing, we did (and this kinda shows that the last bunch of stuff wasn't required to do this, but it was still useful longterm) `poe run > templates/test.html`, and we saw that the vanilla.css file was appropriately found and picked up when we opened the created file
            - As expected
        - So we need to instead return the css inline with the response? Perhaps jinja has a way to do that natively, or perhaps this is something that lambdas support
            - Ah shoot, duh, yes they support it -- the href is just telling the browser to make an additional call to another path on the same host. So we can support it by making the lambda respond appropriately to a request to the `/vanilla.css` path (or, better yet, not reference it as `vanilla.css`, call it `stylesheet.css` or something and then just point to the appropriate stylesheet in code)
                - This seems like a really great, clear thing for Claude to do.
            - Also, the site looks really ugly with this particular stylesheet -- we'll need to find a better one that works better, or just steal what we like from this and make our own
- So now that we've done appropriate exploration, we're going to have Claude update our code to
    1. Check the requested path from the event, serve our base page in response to a GET to the root, and serve vanilla.css in response to the /stylesheet.css path
    2. Update the template to reference stylesheet.css instead of vanilla.css
    3. Update the name of the vanilla.css file to stylesheet.css

## 2025-06-11

Yesterday was a big success -- the prompting went swimmingly, and Claude made the updates appropriately. We achieved both our goals for the day. I have not yet pushed the updates to AWS, but that shouldn't be an issue (okay, this might be an issue -- we'll need to actually test that the updates work). So today, we'll push up the updates to AWS, test, maybe do something about the fact that it's still really ugly? (And honestly kinda worse with the new stylesheet, maybe we should find a better one, or let Claude just generate one). We should also add in POST requests.

Goals:
    -[X] Push updates to AWS
    -[X] Test updates
    -[X] Make any fixes needed
    -[X] Figure out POST request requirements
    -[X] Prompt Claude to add them

- Pushing updates should be easy -- we'll just use our poe command
- Testing will just be opening the page and confirming it looks appropriately different (and awful)
- Fixes will be based on testing
- POST request requirements will be the fun thing for the day
- We need to
    - Update the form to have a submit button
        - We will want to use the PRG (POST-Redirect-GET) pattern to avoid double submissions if the page is refreshed
    - Process POST requests in the Lambda handler
    - A POST request should be the relevant information to create multiple CollectedRent records
        - We need to design the JSON contract for it
        - We need to design the SQL command
            - We'll want to use the executemany function in the sqlite3 Python module to batch add records
        - I'm not a huge fan of how it's currently set up, that we're going to log rents that are collected, rather than recording the updated state of the world
            - Updated state of the world is nice, because we know that we're only going to have a single writer (concurrency = 1), so one of the benefits of having these one at a time additions is moot
                - That is, if we had multiple writers and we didn't have guaranteed consistency, one at a time additions would allow us to keep the updates atomic, vs state of the world could have inconsistencies
            - Updated state of the world allows us to have idempotent updates -- that's harder to do with one-at-a-time
            - I'd really like to have idempotent updates -- idempotency eliminates a whole category of issues
            - Perhaps we could have idempotency by passing the expected value of the amount due?
                - This might still be an issue if the client is incorrect -- like if the client had gone back to a previous page, and the user still wanted to add in a rent. The user doesn't care that the number on the page is wrong, they just want to add in the fact that they gathered a rent
            - Perhaps we can just show a log of collected rents to the user -- we expect there to only be a few per unit per month, so showing the rents that were collected would allow the user to validate and modify any CollectedRent records
    - Okay! So we will add an additional requirement, that we will show the CollectedRent records on the UI, and allow the user to edit or delete (soft delete) records from the UI

- Ideating done, let's execute.
- Pushing up updates now
- Testing success, it looks new and gross

Okay, POST request requirements:
1. Update the UI with a submit button that will submit the form, then redirect the user back to the original page
2. Update the UI with a hidden input to uniquely identify each Lease that a CollectedRent record should be added to
3. Extract the db and s3 connection code into a function that will connect to s3 and the database a single time, cache them, and then just return the cached database and s3
4. Update the Lambda handler in app.py to handle POST requests by
    1. Using our new function we made above that caches our db and s3 connection to ensure that we have the database and s3 connections available
    2. Parsing the body of the request as JSON
    3. Update the database using a parameterized query, and all of the units that have a non-zero collected rent in the submitted form (there may be multiple)
    4. Store the db back to s3

We should also think about wrapping our db connection in a class that abstracts out the pull and store back to s3 process -- this would be a great place to also put our caching code, so that we can let the class lazy load and just use it regardless of warm or cold state.

Prompted Claude with the above requirements -- I was a little bit wrong about what was needed, I had already considered linking the forms in the UI back to the units, but sadly I used the unit.name instead of the lease id -- Claude got a little bit confused and is not doing great on editing index.jinja. I'll have to go in manually and clean it up.

I also need to put back in the comment about why we're allowed to treat the db like this (downloading and uploading it from S3 like we are without actually caring about the difference between the local db file and the one in S3)

[X] Need to also remove the lease_ naming that Claude added in index.jinja -- it's unnecessary and adds an extra step to processing

Some small asks to Claude, and I like index.jinja again. I have some concerns about the actual logic that was implemented for the amount (why are we calling `float` on the amount? It should already be a number, if we're trying to validate let's do some real validation instead).

## 2025-06-13

Okay, back in this.

We did not commit our work from last time. Should we? I like to have a known good state, but WIP commits at the end of every touch would also be very useful. Most likely, what we should do is a branch and merge pattern. I'm going to implement that here, and we will start doing feature branches (even though we're kinda still pre-MVP, which is where I would normally want to do that).

-[X] Create new branch for POST requests
-[X] Commit work from previous day

We completed our goals from yesterday, in that we determined POST request reqs and prompted Claude for them -- we have not, however, really taken a good look at the updates, and we still need to test

-[] Review Claude updates (can view as a PR concept)
-[] Test Claude updates

Considering the way we're playing with this, it may be valid to add in an additional, dev stage, to be able to freely deploy and test without being concerned about affecting actual functionality -- however, we still don't have any users, so it's premature at this point to be precious about our "prod" stage. We'll update to have a dev stage once changes actually matter.

Does it make sense to commit this lab notebook to the dev branch? I think that it makes the most sense to always commit this to master, but that's... kinda not how git typically works. Is this a space that I should be looking into git-worktrees? My understanding is that they are the go-to for AI Agent prompting, but I don't know much about them. I've also heard that they're a bear to set up. We'll throw that in as a goal, but it might not be a today goal

-[X] (stretch) Research git-worktrees
-[X] (stretch) Write brief on git-worktrees
-[] (stretch) Set up git-worktrees

Could I just have Claude do the research and brief for me?

-[X] Prompt Claude to research and write up documentation describing git-worktrees. Include how to set them up in a Linux environment, and how best to utilize them in an AI agent coding setup. Include links to references.

Okay, Claude is working on that. We'll see how much that costs me, and how useful it is. Honestly, this may be a place where it's more useful just to google for it, because the MO of the internet is just uploading AI slop for free...

I'm going to commit this journal to master, then create a dev branch for us -- if worktrees is good and useful, we'll use it after this session. Claude finished -- it cost 10 cents to create the guide.

Worktrees look really nice, actually. This will also resolve my concern about where this lab notebook gets committed -- I'll just have this open in the master brach worktree, while the code is open in the feature branch work tree. We shouldn't run into merge conflicts, since Claude won't update this file (and if it ever does, I'll update CLAUDE.md to tell it not to).

I've already committed to using them after I finish this feature branch, which is good because I don't want to get distracted now

I've made some small updates to add type hinting and clean up some minor diagnostic errors. I likely could have asked Claude to do so, but this was quicker (and cheaper!)

I also want to ensure that Claude's use of parameters in the event object are correct -- I checked out the AWS docs for lambda function urls

I copied the payload down to lambda_function_url_event_structure.jsonc, and then asked Claude to copy the descriptions for the parameters down to comments in line with the parameters in the file. It cost 12 cents, and I should have pressed it a little further, because it didn't set any of the sub-keys. I'm going to try to use the resume functionality, hopefully it'll still have everything in context

Resuming doesn't quite do everything I'd want -- it looks like the messages are placed into the context, but nothing else. Claude had to redownload the aws docs, and reread the jsonc file

Claude told me that it needed to do an extra call to be able to comment the subkeys -- I didn't let it, it just wanted to download the total docs instead of the docs at the anchor point I gave it. I described the table it should use, I hope that it finds it.

I kinda think Claude didn't figure it out -- it put in many descriptions that didn't precisely match the docs description. I don't know if it's just paraphrasing, because me asking it to EXACTLY copy the descriptions was too far back, or it if couldn't find the descriptions in the table because the parameter names are a little bit different. I've reprompted it to copy them EXACTLY.

It's asked to refetch the docs. Lord, hopefully it works.

It didn't, and I've terminated that session -- I've heard that allowing the AI to continue trying once it's screwed up will just have it continue to screw up, because the error is in its context window. I've opened a new session, and given it the following prompt to hopefully fix this (we're down another 26 cents)

> Please update the ./docs/lambda_function_url_event_structure.jsonc file to include the EXACT description for every key and subkey found in the AWS_docs_table.html file. For example, the `version` key in the lambda_function_url_event_structure.jsonc file should have the comment `// The payload format version for this event. Lambda function URLs currently support payload format version 2.0.`. Please update any existing comments to match the EXACT description in the table. Parameters in the AWS_docs_table.html file including a period (such as `requestContext.authorizer.iam.accessKey`) refer to a nested structure of objects, where each period-delimited component references a key of the nested object. For example, `requestContext.authorizer.iam.accessKey` starts at the top-level key requestContext, the value of which is an object; we then descend down to the authorizer key inside that requestContext object, the value of which is an object as well; descending futher in the same way, we go to the iam key, and then to the accessKey key. It is on the accessKey line that we add the comment `// The access key of the caller identity.``

It then properly created a todo list of the different things to comment, and followed through on each of them. This seems to have worked appropriately, and we now have a lovely document recording how the event object is structured. All for the low, low cost of another 35 cents.

Christ. Did I really just spend most of a dollar on this crappy little jsonc file?

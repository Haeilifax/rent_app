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
- NB: See header 2025-06-17 for why we're using float

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

## 2025-06-14

I'm going to set up worktrees, because I'd really like them for this notebook -- I just commited the notes from yesterday, and then when I switch back to the feature branch they were gone (duh).

I appreciate the doc that Claude made, but I dislike how much time is spent on the "how" rather than the "why". There's a lot of bash commands, rather than rationale and explanation. It _is_ nice that there are commands specific to the project at hand, and it's tailored exactly for me. But also, I don't how much to trust it. I would rather have the official docs in front of me, or a human who is going to be wrong in predictable ways, but I don't really know how to predict when Claude is wrong or going to be wrong.

Official docs: https://git-scm.com/docs/git-worktree

Claude very much likes the `-b` option, which creates a new branch when you're making the worktree. Can you make it create the folder as well? Or do you have to `mkdir` first?

(to note, you can make a worktree off any commit or tag -- branches are just convenience for them)

git will also default auto-create a branch if you don't pass it a name, but it will use the pathname of the directory, which is probably not going to be exactly what you want

Worktrees actually seem... really simple? I'm not sure where I had heard that they were complicated, but this seems bog-simple and something that I wish I had been using for ages? (they were just added in 2019, so not unreasonable that I haven't used them)

All the examples I've seen so far imply that worktrees should be outside the git directory of the main-worktree -- is this a requirement? Does this make life easier? I guess there's no good way to exclude the worktrees via .gitignore (actually, yes there is -- the branch name is unconnected to the path name).

Okay, so idea -- make worktrees inside the main-worktree, with names of `worktree-{branchName}`. Add `worktree-*` to the .gitignore.
- Claude says don't do this -- nested git structures might confuse commands.
- It's so neat and clean that I'm going to look into it a little harder anyway

Okay, confirmed, _not an issue_. Also, just learned a new tidbit about the .git/info/exclude file, which is a local only .gitignore? I've definitely run into situations where I've put things that would only really be seen in my local environment into .gitignore to have them not show as untracked, so this will be appreciated

Annnnnnnd done??? That was stupid easy
`git worktree add worktree-feature_AddPOSTRequest/ feature/AddPOSTRequests`
`nvim .git/info/exclude` (added `worktree-*`)
`cd worktree-feature_AddPOSTRequest/`

Now I can just use that folder as my work space for actual updates

Hmm. Okay, looking at Claude's updates a little bit, he imported something in the body of a function -- obv we need this to go at the top of the file instead (there's no reason in particular to lazy-load it, it's standard lib), but what's the best way? I think it's got to be a comment placed in the text of the code, maybe using the `AIDEV` format we saw previously?

I don't think that's going to be the way. To be continued next time.

## 2025-06-17

It's so nice that this is just directly in the master branch, without me having to be concerned about it

Also, showing the utility of this notebook, I don't really remember current context, and I'm going to look back over my notes to figure out what's going on, what I was planning to do, and what I need to work on

I don't think I ever confirmed whether git-worktree will automatically create a new folder -- going to test now

-[X] Test if git-worktree creates a folder when you run it

Confirmed, it does automatically create the folder

I don't think it's worth it to create the scripts that Claude suggests (probably as poe tasks), at least for right now -- I'm not going to be creating them frequently enough, and I'm not going to have Claude creating them, so it's best that I do it manually and learn

In order to create a new worktree and branch, run

`git worktree add -b {branch-name} worktree-{branch-name}`

In order to remove a branch, delete the folder (can only be done once folder is clean, that is no pending git changes or untracked files) and run

`git worktree remove {branch-name}`

Goals for today:
-[X] Finish reviewing Claude's code
-[] Test Claude's code
-[] Push up to GitHub

We've re-set up our Neovim windows -- it's annoying that I can't just have them all spring back to life when they get closed. Should I start using session, or start using tmux?

What's the best way to review changes? Obviously, once I push things up to GitHub, I can make a pull request and look there, but that doesn't make me super happy -- I'd love to have a way to review changes locally, akin to GitLens in VSCode.
- Maybe I just use the diff tool? Since I'm using worktrees, it's incredibly easy to just run diff (or look for a prettier diff tool)
- Is Magit an option? I don't really know what it does, but people are very big on it
- I'll look at other options as well

-[X] Look into using Magit / another local-first PR tool

[Magit homepage](https://magit.vc/)
- Magit is a text interface to git
- Replacement / missing link between CLI and GUI git interfaces
- Just runs git commands under the hood
- I've seen Magit recommended pretty broadly in the past
- Emacs-based? How annoying will it be to use it without necessarily using emacs? Will I need to learn new bindings? Can I incorporate it into NeoVim?

[Magit, the magical git interface](https://emacsair.me/2017/09/01/the-magical-git-interface/)

- I'm a little bit uncomfortable with Magit being mostly "mnemonics" (which reads as hotkeys to me), because the discoverability is so much worse in a lot of these cases
    - I'm running into a lot with Vim where I know what I want to do, but actually executing requires me to know about multiple keys that do things I don't know, and I don't know of their existence
    - I would love to just be able to type into a command "thing I want to do", and have a key sequence and explanation spat out at me (with optional "just run it" as well)
    - Space for LLM? Maybe I should build a plugin (or find one)
- All information is actionable -- no "read-only" buffer
    - Sounds similar to the file viewers in NeoVim (I'm using mini.files right now, but I think others work similarly), where you create new files but just adding a new line, move files by cut and paste, etc
- Magit is a nearly complete Git interface
    - Nearly anything that can be done with the CLI can be done with Magit
- One thing I'd really like from Magit is easily dealing with hunks (which I was able to do with VSCode, but seems like a bear through the CLI)
-

(I need to set up the correct mechanism to exclude counts from gj and gk remapping, because relative line numbers make it so much easier to use)

[Magit Walkthrough](https://emacsair.me/2017/09/01/magit-walk-through/)
- Magit has ability to easily stage hunks
- "Magit requires a little knowledge of emacs, but not a lot"
    - Yeah, but do I believe that?
    - Can I have Magit but with vim bindings?
- There's a discoverability window, "popup of popups" under "?"
- Ability to commit easily in Magit
- Ability to amend previous commits
- Rebase, with additional useful features
- Merge features exist, but aren't dove into heavily -- `preview merge` is an option (how nice is it?)

Amazingly, I don't think I'm going to use Magit
- Seems annoying to use because it requires some emacs knowledge
- Seems kinda bulky?

Just installed tig, which is a command line tool that seem to do a lot of similar things in terms of interacting with git (without necessarily being an editor as well)

[tig Homepage](https://jonas.github.io/tig/)

Let's start up updates for Claude to make to his PR:

1. Please update the import on line 104 to be at the top of the file
2. Remove comment on line 109 that no longer makes sense
3. Update the block at line 169 to only upload to S3 if there are changes to the database (in addition to the ISLOCAL criterion)

(We've just learned that tig gives us all wrong line numbers...)

Let's also start updates that I should make:
1. Make it clear in CLAUDE.md that all imports should be made at the top of the file, unless it's needed to be imported elsewhere for optimization

Do we need to use urllib to parse qs? Submit button will submit as www-(something something something) -- google search says www-form-urlencoded, which is name=value and joined by ampersands (probably html-escaped as well?). parse_qs does parse exactly this (see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.parse_qs). It will turn a www-form-urlencoded query string into a dictionary of name:value pairs

Just noticed and recalled -- Python docs have GNU Terry Pratchett, we should make sure to add that

-[] Add GNU Terry Pratchett header

Ah -- we questioned the use of `float` earlier, and it's because we'll receive the form values as all strings (because of the www-form-urlencoded nature). Adding a note above

I appreciate that Claude used the 'start of month' sqlite function on their(? How should I reference the AI?)

tig seems to give all wrong line numbers in the status bar -- maybe it's giving us line numbers of the total diff? Or giving us line numbers in tig? But the first line of app.py is line 31 in the status bar...

Okay, I've given the prompt above to Claude. Had to correct him because of the wrong line, and then corrected him again because he checked if records_to_insert was empty twice, instead of just doing the ISLOCAL check inside the original check. I also had him commit his work. Cost was 19 cents (one of my cheaper commits). I'm now going to test this

I'm going to start off by testing locally, to ensure that there aren't any directly silly mistakes (like a sqlite error because the given SQL doesn't actually work). Assuming that looks good, I'm going to push it up to Lambda, and test directly against it there with the real page.

OH, and let me make a goal to update my neovim

-[] Update neovim to allow {count}j and {count}k to go by real lines, vs visual lines (currently they're always remapped to gj and gk)

To test locally, I'm going to make a test payload with lease id and amount, and another one with a lease id and a blank amount
- I expect the default to just be a blank, interpreted as an empty string, but we'll see when we go to deploy and do a real test.

We're just cloning the event structure that we commented -- we don't have a jsonc parser in our python though... That's awkward.
- I don't think I want to write a jsonc parser right now
- The way I've interacted with jsonc parsing previously was a substitution that would remove all comments and trailing commas from the jsonc document, then parse it using the builtin json library
- I'll just remove all comments manually using a vim replace, since this is test data (not dynamic)
- Command: `:%s/ \?\/\/.*//g`

Will we have an issue with passing a number as the lease id without directly converting it to an int in Python? It'll just be matching as a string
- I believe so -- I'll give it a test, and then we'll prompt claude to update it

I don't want to check the path in the POST request yet -- this is something that will be necessary eventually, but as of right now, it's just noise and makes our life worse. We'll likely not even have post requests go to the root path, instead differentiating them in a REST-y kind of manner (so that we can also manage the database via POST calls)

Starting new prompt for Claude: (I'm setting these out by an extra newline so that I can just `yap` them)

1. Please remove the path check on line 94

I'd like to build an actual test infrastructure on this -- testing is something I'd like to be more experienced in, and it's a crucial component of using LLM's (according to many things I've read). Test Driven Development is also frequently called out as something useful for agent use, and is something that I was interested in previously.

I'm going to research quickly testing frameworks for Python and pick one. Currently, I know of pytest (which I expect to use -- last I checked, it was feature-rich and easy to use), unittest (standardlib, previously known as nose I believe?), and hypothesis (property testing, I've toyed with it in the past but it needs the right project and setup to really shine).

-[X] Research testing framework
-[X] Add testing framework to project
-[] Create initial unit test of POST request functionality with testing framework
-[] Create unittest for GET /stylesheet.css (should return a css file)
-[] Create unittest for GET / (should return an HTML file)

Resources:
https://docs.python.org/3/library/unittest.html

llm question:
`What 5 python testing frameworks are most popular, and which would be recommended for a new project being spun up?`
- Recommends pytest
- Calls out unittest, nose2, doctest, and hypothesis

https://old.reddit.com/r/learnpython/comments/ugyqv4/unit_testing_best_practices_good_examples/
- Recommends pytest
- Wow reddit can be garbage, just the blind leading the blind
- Thank you to the redditor calling out realpython

https://realpython.com/python-testing/
- Starts with description of testing
- Calls out doctest
- Brief descriptions of unittest, nose2, and pytest make it sound like pytest comes out the winner again
    - Get to use default assert statments
    - Fun little quality of life things like starting from first failed test
    - plugin ecosystem
- They suggest making a separate test directory (my plan too)
- Call out Single Responsibility Principal -- we'll get to that once we have a product
- Fixtures are reusable testing objects -- yes, we'll remember this
    - With fixtures -- we should make sure we set up a new sqlite database every time
- Tox!
    - Been a while since I've heard that name
    - It's not going to be relevant for us here, we aren't really trying to target anything other than our own server. Environment differences would look more like trying to run directly in a docker container mirroring the Lambda function enviornmnet
- Linting
    - I'm using ruff as a linter / autoformatter
    - I should have either a git hook, or tell Claude to run it after every pass
- Benchmarking
    - Useful, but not right now -- we'll deal with that when we have a product that we actually care about performance on
    - Not using cold-start lambdas is the fastest speed up we can get right now
    - We can also benchmark inside of pytest using a plugin, so that'll be even easier -- `pytest-benchmark`
- This is a really cool mock for requests: https://github.com/getsentry/responses
    - Lets you mock API calls (like Apex had with their testing framework)

Is it time to refactor, to pull the GET and POST request handlers out into their own methods, and possibly even break them down further from there? Maybe -- it would be gross to test using a whole integration test everything, but also we should be cognizent of how much time we're wasting before actually having a working product (yes, yes, it's a little late to be saying this now). We'll put it on the backburner

We'll update these items with completion dates once we turn them into daily goals and complete them

TODO: Refactor main method to not be a giant, undifferentiated pile of code. Break GET and POST request handlers out.
TODO: Make response function to build success and error responses without manually building a gross dict

How do I import my app? I don't really want to install it into my virtual env, and I don't really want to make a gross relative path.
- Do I just take the hit and do an editable install? I don't think that sounds pleasant
- I'd like a little magic please...

Resources:
https://docs.pytest.org/en/stable/getting-started.html
https://docs.pytest.org/en/stable/explanation/goodpractices.html#goodpractices
- Okay, it wants an editable install :(
- Editable installs with uv are possible, I think?
- Is there other advice for use with uv?
- > For new projects, we recommend to use importlib import mode (see [which-import-mode](https://docs.pytest.org/en/stable/explanation/goodpractices.html#which-import-mode) for a detailed explanation).
    - Minor benefits, unlikely to affect us (allows for having duplicate test file names across different test folders)
    - But may as well
- Calls out using a full src style layout
    - Should we move to this? We're at a light level, with a lambda folder, but we can drop a layer (and need to update our terraform doc)
    - Recommends [this blog post](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure%3E)
        - I read this blog post already, years ago when I was first self-teaching
- Shoot, with an editable install, will we need to wrestle with resources to get the templates to work correctly?

QUESTION: with an editable install, will we need to wrestle with resources to get the templates to work correctly?

https://docs.pytest.org/en/stable/explanation/anatomy.html

> You can think of a test as being broken down into four steps:
> - Arrange
> - Act
> - Assert
> - Cleanup

- Arrange you set up the dominoes
- Act you knock them down
- Assert you validate that they made the shape you want
- Cleanup you pick everything up so the next test can start clean

## 2025-06-18

I'm going to just dive into tests, instead of reading the whole docs first

My understanding is that I'll want to do an editable install, and I'm concerned I may run into issues because the script needs a resource that might not be appropriately handled

I'm going to start with an editable install -- I believe I can do this through uv
`uv pip install -e .` (see https://stackoverflow.com/questions/79418598/how-to-do-install-my-custom-package-in-editable-mode-with-uv or better yet, https://docs.astral.sh/uv/pip/packages/#editable-packages)

We immediately hit an error from running that command at the top level of the worktree -- automatic discovery found too many possibilities, and suggests setting up a find directive or a src layout

We're moving to src layout -- I believe that will mean we don't have to do an editable install at all

In order to move to src layout, we need to:

1. Create a new `src` folder
2. Move our lambda folder into the src folder
3. Rename the lambda folder to 'rent_app' (for clarity)
4. Update our terraform file (main.tf) wherever we reference the lambda structure (such as in the archive data resources)
5. Update our poe tasks in pyproject.toml to reference the new structure
    - Since we'll have the package installed as editable, we won't need the `cwd` property anymore
6. Review the workspace to ensure there aren't other references that need to be updated

Passing the above to claude

Claude did a good job -- minor notes required to make sure he left in the cwd for one task that needed it, though honestly that's another thing that might have to change
- (we're currently having the local test database inside the lambda folder, which is causing additional unnecessary size for our lambda pushes and may cause issues now that we're trying to run this as a package)

I'm going to update the CLAUDE.md file to explicitly say not to review the lab_notebook.md file unless otherwise directed, as these notes are merely documenting the process and should not be necessary for his purposes

-[X] Update CLAUDE.md to tell the AI not to look in lab_notebook.md unless directed

I also just found that we're expecting to have a JSON body in event in our CLAUDE.md, rather than the actual (default) www-form-urlencoded. I've updated that as well

Next step, editable install, and then tests

-[X] Make editable install
-[] Make most basic test to determine feasibility

Editable install went smoothly

Okay, most basic test possible. We're going to test getting the stylesheet, which is a GET event with path of `/stylesheet`

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

## 2025-06-21

Today, I want to

-[X] Push code to GitHub
-[X] Make goals checklist doc, so that I'm not stuck just scrolling to find old goals that I still want to accomplish (This is slightly different from a roadmap doc, because it's going to be on a grittier level)
-[] Write the basic GET test

Pushing to GitHub should be easy enough -- haven't played around with it in a while, but BitBucket the process was to make a new repo that was empty, then link to it as a remote from my local git, and push. That's going to be the basic process I attempt.

I don't think I have an SSH key set up from this machine in my GitHub -- going to add new key. I expect there to be instructions how to do it on GitHub, but I expect it to be: generate SSH key with ssh-keygen; upload key to GitHub.

No directions on GitHub -- I'm going to google for it, I could probably wing it and be right, but security is one of those places that I'd prefer to be actually correct.

https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

The provided command is `ssh-keygen -t ed25519 -C "your_email@example.com"`, to generate an edDSA key. I'm not going to tag it with my email, so I'll use `ssh-keygen -t ed25519`

Done, created key then copied to clipboard -- a little annoying that it's not the default method, but `xclip -sel c < {input_file}` copies a file to clipboard

Now I need to tell git to use the key to push to GitHub -- I believe I can do this with the hosts file, but it's probably easier just to set some kind of global variable in git (I'm not planning to have multiple keys connected to GitHub on this computer)

https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection

Hmm, am I silly? Will it just auto-try each of my keys? That... doesn't sound correct, but let me give it a try with `ssh -T git@github.com`

That failed, and I think the reason is that they expected me to a) use the ssh-agent (which isn't a bad idea) and b) use id_rsa or other default name for my key (which would be automatically loaded by the ssh-agent)

https://stackoverflow.com/questions/23546865/how-to-configure-command-line-git-to-use-ssh-key

Ahhhh, yeah, not the hosts file, but the ssh config file

Yep, editing that allows the ssh -T to work. Testing the git push now

`git push -u origin master`, and then cd'ing down to the worktree `git push -u origin feature/AddPOSTRequest` worked perfectly

Code is now pushed to GitHub, moving to making a goals doc -- I'm going to keep this in master with this lab notebook, these goals could span multiple branches

Okay, created goals doc. Moving on to the actual meat of the matter, creating tests

So what am I doing here? I'm going to create a basic test of the GET /stylesheet functionality. We're going to test running the lambda_handler function with an event that has the GET method and the /stylesheet path. Right now, this is an integration test -- once we break out the GET functionality (and likely break paths out further), we'll be able to do unit tests.

In order to test this, we need to import our module with our correct environment variables set up, and we definitely need to update our code to use resource imports instead of just directly reaching out with file paths -- otherwise, we're not really testing our app, we're going to be testing how similarly we can set up our testing environment to the app's environment. Maybe we have ISLOCAL take a db location instead of just true? That way, we can remove the database from our app folder and still be able to reliably test

To note, we're not going to use Claude for generating any of our test code -- Claude will not touch the test directory at all (we should add that to his CLAUDE.md as well). This is because tests encode our design specs for the product, which is our responsibility, not the AI's. This also helps prevent the AI from just rewriting failing tests to make them pass. See https://diwank.space/field-notes-from-shipping-real-code-with-claude for more details

-[] Add text to CLAUDE.md telling Claude not to update any file in the tests directory

We're going to
1. [X] Update our code to use resource imports for the templates and stylesheets
2. [X] Update ISLOCAL to take a db location (which can also be `:memory:` for easy testing)
3. [] Set up environment variables in our test code before we import the rent_app package to use ISLOCAL
4. [] Set up our database as a fixture
5. [] Import the rent_app package in our test code
6. [] Create a test function that runs lambda_handler with an event w/ method=GET and path=/stylesheet

We can use Claude to do the first two, but before that I'm going to look up resource imports myself, because I believe the way I've done them in the past is now deprecated, and I want to make sure Claude won't fall into the same mistake.

https://docs.python.org/3.11/library/importlib.resources.html
https://importlib-resources.readthedocs.io/en/latest/using.html
- importlib_resources is a backport library of functionality added in 3.7
- Docs have more details on how and why than baseline python docs
- Pretty simple, can just reference resources inside a package. One oddity is that this seems to be referencing resources from outside the package -- am I wrong? Is this not the way to reference resources you're importing inside the package, to ensure that they'll be correctly and consistently imported?
- The `files` API was added in 3.9, and is the new approved way of accessing resources (re:my point before about the way I've done it previously being deprecated)

So, if my understanding is correct, we'll be able to import importlib.resources, and then access the templates and stylesheet with importlib.resources.files().joinpath('templates').joinpath('stylesheet.css').read_text()

Hopefully this is also what (or similar to what) jinja is doing with their template loading

We've made the update for stylesheet, let's manually test raw (running in the appropriate location), and then also test importing it and running it

We... didn't test run this since we made some updates to the type signature of get_db_and_s3 -- we forgot to use from `__future__ import annotations`

And we need to also update our `get_rents.sql` to use importlib.resources. Let's take a look through the doc to see if there's anywhere else (besides the database connections)

And I think that our directory changes caused our jinja template loader to stop working -- we just got an error complaining about not being able to find the package `app`, which, well, makes sense. Should be able to update to rent_app? Or maybe rent_app.app? I'll test both, and then start researching if it fails
- rent_app worked!

Okay, most basic test of the `/` path worked! Now let's try to run this from a shell located outside the src directory, importing the module

Trying to import rent_app in the shell shows that it has nothing in it -- we need to make sure we do `from app import *` in the `__init__.py` module to have it show like we want it to
- it's actually `from .app import *`, we need to be explicit about the relative import

Testing in iPython -- Success! The `/` path is failing (appropriately) because we still haven't updated the database paths to be given by ISLOCAL, but the `/stylesheet.css` path works!

We'll commit this, then ask Claude to add the ISLOCAL db path

Claude prompt:

Please update the ISLOCAL environment variable to be a path to a database file. Use this path instead of the hardcoded path in app.py, and update other locations in the project (such as our poe tasks) to take into account this change. Ensure 

Okay wait, this is bog-standard and pretty easy -- writing it out like this it would be easier just to do it.

Hmm, `poe run` is emitting a warning -- `<frozen runpy>:128: RuntimeWarning: 'rent_app.app' found in sys.modules after import of package 'rent_app', but prior to execution of 'rent_app.app'; this may result in unpredictable behaviour`
    - Seems to be due to us using the -m switch, which is causing the package to be imported twice (imported first, and then imported again in our `__init__.py` file)
    - Can we just... not use the -m switch? Or, if we're married to it, we could move to using a proper `__main__.py` file.
    - Let's move off the -m switch, and instead due an explicit python command -- we may need to set up more in the future
    - If we find ourselves doing more than just stupid simple run / testing with this, we may want to make a `__main__.py` file with a cli interface built in

We're not finding the correct db -- we've probably got our path set up wrong
    - Actually, it was just that we set up for a db that didn't exist yet -- just needed to run `ddl.sql` on it

Taking a look at the results, we'll need to make sure we start interpreting None as 0 for the values of the amounts

Okay, poe run is now running correctly, with a db chosen via the ISLOCAL environment variable, with no warnings

We're well past the point where the name of this branch makes sense -- We should break "adding testing" out to a separate branch

We'll need to do some exploratory testing to figure out how to do this with Neogit, but it should be valid.

That... was a harrowing experience, and I think I'm going to wipe all of it out. It would be slick and clean to have the tests in their own branch, but I don't think it makes sense, especially when it involves a change of the directory structure. This could have been better if I had made better commits (ensured that only one thing happened in each) and if I had a tool that felt better to use for this. I think that this is where a gui git tool would really shine -- I would love to be able to use a mouse to just drag commits between different places, have it recalculate the conflicts, and then go from there. I also think that anyone directly espousing neovim or vim is ignoring the glaring issue in discoverability for commands -- there's no way for me to know what I can do next, especially in context-dependent situations. I want to be able to describe what I want, and have the editor give me a combination. LLM built into neovim?

Things we learned here: git mergetool doesn't work directly on my computer, it thinks bc is available but isn't -- instead I need to use `git mergetool --tool=nvimdiff` in order to get a merge editor

Choose from LOCAL (the file you're merging into, in the target branch), REMOTE (how it looks in your source branch), or BASE (the common ancestor of the two) using `:diffget {first two chars}`

Go read this whenever you need to rebase again https://git-scm.com/book/en/v2/Git-Branching-Rebasing

`[c` will take you to the next change in the diff

Rebasing is making copies of commits replaying the effects of that commit onto the current history

When you need to do this again, get a better tool (diffview.nvim looks nice?)

## 2025-06-22

Short session today. We're actually going to get something done.

Step one, we're going to actually write the GET /stylesheets.css test

Step two, I don't know if there's going to be a step two

-[] Write GET /stylesheets.css test

Can we set environment variables using some kind of pytest config, instead of setting them directly in the module?

https://docs.pytest.org/en/stable/reference/reference.html
https://docs.pytest.org/en/stable/how-to/monkeypatch.html

Not with a pytest config, but by using a fixture with `autouse=true` we can monkeypatch the environment to have a particular value. I wonder if this is in anyway better than just having the environment variable set by default -- I guess it's possible I don't understand how pytest works, and just having the environment set in the body of the test module wouldn't do it? Or, actually, no -- it's that if you're testing with multiple test modules, you don't want to change the environment for all of them, necessarily, so having the fixture would help with that. Since we're always going to want these environment variables set, we should actually set them as part of the test task (and make sure we always run tests with the task).

We're setting up a nasty footgun, having our default behavior reaching out to production S3. We should update to change that after this

-[] Update to only reach out to S3 if explicitly told we're not running locally

See line 39 for why we can't set the environment variables directly before the ipython in the poe dev_env task -- poe reads the environment variables as us trying to run them as commands

Setting up the database -- we want to do that once, and have it revert to that state whenever we need it again. That's trickier to do with this real database -- consideration is having an in-memory database. Will multiple calls to sqlite requesting :memory: give the same database? I don't think so, I expect it to generate new ones in that case. We also don't want to spin up new databases every time and fill them with data. Can we have a file as a fixture? That pytest will store the state of and revert to it after each run?

https://stackoverflow.com/questions/74921132/how-to-populate-db-from-fixture-before-test
https://stackoverflow.com/questions/70543525/pytest-how-to-create-and-read-a-file-inside-a-test
https://medium.com/@geoffreykoh/fun-with-fixtures-for-database-applications-8253eaf1a6d
https://stackoverflow.com/questions/57443993/use-single-in-memory-sqlite-connection-shared-among-all-unit-test-modules
https://stackoverflow.com/questions/1037924/populating-sqlite-in-memory-for-unit-testing

I think what I'm going to go with (and this is kind of suggested by the last link) is
1. Create the SQLite file in a temp dir (with the pytest temp dir functionality)
2. Fill the db with data
3. Read the file as bytes
4. Use that output for a fixture that will write the bytes to a new temp file every time, and set ISLOCAL to that temp file's path

I think that I can run it once by using pytest.fixture(scope="session"), but I'll need to dig into the docs a little further to confirm that

Yeah, but lets use scope="module" instead, in case we need to use a different database elsewhere.

Using temp dirs: https://docs.pytest.org/en/stable/how-to/tmp_path.html
- Oh cool, it's just a standard fixture

Using monkeypatch: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- Oh cool, it's just another standard fixture

Oh goodness, getting the real path of a Path, what are we using these days... Absolute? It looks like absolute is fine for 3.11 and after (which we are), but might still be reasonable to use resolve?

Lordy, `ScopeMismatch: You tried to access the function scoped fixture tmp_path with a module scoped request object. Requesting fixture stack:`

Okay, time to google what we're supposed to do to get a temp path in a module scoped fixture...

## 2025-06-30

-[] Start interpreting None as 0 for Amounts (not today)
-[] Set up database as a fixture

https://docs.pytest.org/en/stable/how-to/tmp_path.html
- tmp_path in module scoped fixture is done by using a temp_path factory
- tmp_path preferred vs legacy tmpdir (Path object vs legacy object)

Easy, update to use tmp_path_factory vs tmp_path

Okay, updated code to use that (create a temporary path with tmp_path_factory.mktemp, then use that to connect to). Testing again shows that now we're running into an issue that the Python sqlite module only wants to run one sql statement at a time,

`ERROR tests/test_get.py::test_stylesheet - sqlite3.ProgrammingError: You can only execute one statement at a time.`

https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executescript
- Easy, just use `executescript` instead

And one more error -- one of our temp paths is a directory vs a file
- This shows a misunderstanding of what tmp_path does on my part -- it creates a temporary directory, but I was thinking of it being a file directly (and thus being different than the temp_path_factory fixture)
- In fact, even more so, it looks like we have to explicitly make the things we reference, which does make sense, but I wonder if it will automatically create a path if we don't manually create the folders leading down to it?

Worked! I believe it worked because the tmp_path is already created when the fixture runs, so it doesn't need to be created if you don't create a subdirectory (which they did in the docs above)
- Hmm, actually, let's test that -- sqlite3 will also create the file if it's pointed at one that doesn't exist (will it create a directory structure too? Or just the file?)
    - We'll make a test with an assert, assert temp_path.isfile() (or whatever the correct lingo is)
        - `temp_path.exists()` -- https://docs.python.org/3/library/pathlib.html
    - `assert tmp_path.exists()` does not cause the test to fail, so I think we're correct

Awesome, so we've got green, the test doesn't fail anymore. Doesn't necessarily mean that things are correct, but at least they're not failing, so we should be good to test the /stylsheet.css path

This test is going to assert that we've got text coming back -- we're not testing on the other side of a lambda, so we're not getting the bonus HTTP headers (like filetype or etc) coming back. We also don't really want to test for the existence of anything in particular. I think we just test that the response is non-empty? Issue is, this doesn't show whether we're just hitting the default path or if we actually hit the real /stylesheet.css . 

We're not going to assert anything in the test, actually -- currently, if we fall through to the default it just gives us the landing page, so asserting that it gives us any text back would always succeed. If the stylesheet starts failing to return for some reason, but the test is green, it'll be strange. We can't really fix that, but we can at least make it obvious that a green test doesn't actually mean the piece is working (... Wow, what a bad and terrible test)

Okay, third time we're going back on this -- we're going to import the stylesheet resource directly from the package, and compare that to the output. That will avoid coupling us to the current stylesheet while still actually testing that we're hitting the right location. It does couple us to the directory structure of the package (which we don't like -- that shouldn't be a public guarantee), but we'll take a test unexpectedly failing when we do a big update over a test which doesn't test anything and doesn't fail if something goes wrong.
- We will do this by using importlib.resources, with a package of rent_app, and read from there (like we did in the module itself, but using an explicit package instead of just the implicit "this package" when you don't give a package)

... Wow. Okay. Chalk one up to "using LLM's is dangerous for your knowledge of your own code". We are 100% passing back an explicit body and header and status code in our return.

So we need to change our assertion to be comparing our true css vs the body of the returned dictionary
And we need to assert that the status code is 200
And we need to assert that the content-type header is text/css

We see a type error in the test, because some of the possible values of the lambda_handler dict don't align with what we're trying to do with them (ex. it sees us trying to slice the headers dict, and complains because you can't slice an int). We should update the lambda_handler function with an actual return signature (either of dict[str, Any], or making Claude write up a more complete TypedDict).

And there we have it! A completed GET /stylesheet.css test!

## 2025-07-02

Today, we're going to start pushing on POST requests. We've spent a while digging into tests, and we have a test suite, but I want to get something real done on actually pushing this app. It's also the second of the month, so if I can get the most basic functionality complete today or in the near future, it can provide value immediately.

So goals for today are to manually test the POST request functionality that Claude added (we think we know an issue already, that the lease ids are going to compare wrong, number vs text, but we'll see). Once we've manually tested, we're going to try to find as many errors as possible in a timeboxed 45 minutes, then regroup.

-[] Manually test POST requests
-[] Find errors and issues, and write them here

We have not pushed up Claude's code yet. There will be multiple different avenues that we need to test:
- Does the data pushed by the POST request create the right db entry?
- Does the db save correctly to S3 (persistence)?
- Does the UI push the correct data?

So we need to test not only locally, but also in the browser. We should set up a local lambda server (using Docker, most likely) so that we can test browser based things without having to push up

We haven't pushed from the POST request worktree, so we haven't had to install all the terraform necessities. We should set up a worktree script that will 
1. Create a new worktree
2. Descend into that tree
3. Create the virtual env with uv off the uv lock file
4. Install the appropriate terraform details off the terraform lock file

-[] Set up poe task for creating a new worktree

This would be a good job for Claude -- we'll set it up next time we need to create a worktree

We need to set up a poe task for initializing a new setup, to ease spin up time for new devs (though it's unlikely that any will sign on). It should run `terraform init` with a cwd of the terraform folder, and run `uv sync` -- this can then be used in the poe task for creating a worktree

-[] Set up poe task for syncing a folder that hasn't been developed in yet

uv sync needs to sync `--dev`, otherwise it won't install rent_app (required for testing) -- all the more reason for a poe task

Hmm, actually, it wasn't the --dev option -- checking the uv lock file, the rent app wasn't actually installed as a dev dependency -- fixing that, we don't want to install the rent app in an actual install, only locally during development. I believe the issue with this is actually that, since it's an editable install, it's keying off the current working directory, which is the terraform folder? But this doesn't make sense, uv doesn't care about that, I'd be able to use it from any folder in the project

https://docs.astral.sh/uv/concepts/projects/sync/#syncing-the-environment

Hmm. It looks like uv will actually automatically install the package I'm working on if a build-system is declared. So my editable install isn't necessary -- but is this the reason I'm being uninstalled whenever I sync? Because there's no build system declared?

https://github.com/astral-sh/uv/issues/9518

Goddamn intentional behavior. Ooooo I'm roasty toasty. Okay, declare build system, and we'll be groovy

https://docs.astral.sh/uv/concepts/projects/config/#project-packaging

So we can force it to be installed as a package by adding `tool.uv.package = true` into our pyproject.toml, but that just uses the legacy build system. We'd be better off actually declaring a build tool. 

https://github.com/astral-sh/uv/issues/1626

```
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

but that still uses setup tools. 

https://docs.astral.sh/uv/concepts/projects/init/

```
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```
- The build system used by the default `--package` flag for uv init

This is likely our best bet, but I'd like to see options...

`hatchling, uv_build, flit-core, pdm-backend, setuptools, maturin, or scikit-build-core`
- Option list for uv init --build-backend

https://github.com/astral-sh/uv/issues/13685
https://github.com/astral-sh/uv/issues/9271
https://github.com/astral-sh/uv/issues/12856
https://github.com/astral-sh/uv/issues/11838
https://packaging.python.org/en/latest/tutorials/packaging-projects/
- Python's tutorial uses Hatchling as well

https://packaging.python.org/en/latest/key_projects/#hatch
https://packaging.python.org/en/latest/key_projects/#setuptools
https://packaging.python.org/en/latest/key_projects/#flit
- Flit was my first thought on build tools

https://packaging.python.org/en/latest/key_projects/#pdm
- PDM is a build-system, interesting -- thought it was more of a response to npm

https://packaging.python.org/en/latest/guides/tool-recommendations/
- Lord, unhelpful. Just presents a bunch of options. At least there's links to each of them

https://flit.pypa.io/en/stable/rationale.html
- Simple tool for packaging. Reasonable, makes me wonder though how quickly you leave the realm of simple

https://github.com/pypa/hatch/tree/master/backend
https://github.com/pypa/hatch/tree/master
https://hatch.pypa.io/latest/why/
- Full management tool -- we definitely don't need the full hatch, we're using uv, but hatchling would be fine
- Really only compares against setuptools -- seems like a fine tool, but haven't seen anything that clearly makes it the one to use

https://backend.pdm-project.org/
https://github.com/pdm-project/pdm-backend
https://github.com/pdm-project/pdm
- No info

https://pypi.org/project/poetry-core/

https://old.reddit.com/r/Python/comments/fe04s2/what_do_you_recommend_for_a_build_system/
- Too old to be useful -- 5 years

https://old.reddit.com/r/Python/comments/1jv888t/are_you_using_inline_deps/
- Opened this link because inline deps????

https://peps.python.org/pep-0723/
https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata
- Ahh, lets one-file scripts have additional details. Unimportant to our purposes here, but interesting -- I think I dislike it?

https://old.reddit.com/r/Python/comments/1jv888t/are_you_using_inline_deps/
- Okay, back to this
- Good discussion
- I agree that this is very cool for one file scripts, but mostly on the developer side -- it just removes the need for a full file structure
- I also agree with one of the commenters that I'm not a fan of "magic comments", with impacts on code and special formatting
- One of the commenters was complaining that this requires two different requirements places, one for people using this new structure and one for people not -- another commenter suggested requiring just uv in the requirements.txt file, which would then allow the script to just run. Kinda hot if I wanted to use this

https://medium.com/quansight/pep-517-build-system-popularity-b4daccaa47fc
- Obv setuptools is most popular, followed by Poetry, then Hatchling, then Flit
    - Poetry and Hatchling on the same order
- Since Poetry and Hatch are full featured packaging tools, vs Flit being just a build tool, impressive that it's competing so highly -- I would guess everyone using Poetry or Hatch is using the respective build tool, vs Flit needing to be specfically selected
    - Not even counting the fact that Hatchling is the tutorial choice for both PyPA and uv

https://news.ycombinator.com/item?id=43095157
- Discussion of article about uv
- `exclude-newer` option allows giving a timestamp that all packages must be older than

https://old.reddit.com/r/learnpython/comments/109lwq0/whats_a_good_backend_for_building_python_packages/

Fine. Nobody on the internet actually cares about this. It's entirely commodified, or I guess most people don't need to think about it. We'll use Hatchling, because it's popular and used in tutorials (so if there's anything that people are centering around, it'll be that). I would prefer to use Flit, because it's stand-alone, but I don't trust that it'll sufficiently handle complex use cases (since extending it doesn't involve plugins, but instead creating a new build-backend). I also have a vibe about it that it'll be uncomfortably limiting, that it's primarily made for a small use case that's easy to deviate from.

Going to use the snippet from the uv docs:

```
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Okay! uv successfully installed rent-app

Attempting the poe init task (which will run both uv sync and terraform init).

Success

Attempting poe apply (which will run the terraform apply command)

Failure, goodness, because it doesn't recognize that these things already exist...
I need to generate a terraform state file? Or commit it?

https://developer.hashicorp.com/terraform/language/state
- `terraform.tfstate` is the file name

## 2025-07-03

I'm going to copy the state file down? Or, actually, first I'm going to check through the terraform docs again for what they suggest committing -- we took our .gitignore from Claude, and that might be biting us in the behind, because it seems they may be useful. Perhaps there's another way, though, that a new dev would be supposed to align their tf apply with the resources that have already been created

https://developer.hashicorp.com/terraform/language/files
https://developer.hashicorp.com/terraform/language/files/dependency-lock
https://developer.hashicorp.com/terraform/language/files/override
https://github.com/github/gitignore/blob/main/Terraform.gitignore
- This looks like what Claude lifted my .gitignore from -- interesting that they ignore the state files

https://old.reddit.com/r/Terraform/comments/yxtq02/items_to_include_in_gitignore_when_using_a_cli/
https://stackoverflow.com/questions/67963719/should-terraform-lock-hcl-be-included-in-the-gitignore-file
- This says that the lock file should be included (no details about state file). Am I ignoring it right now?
    - I'm not, explicitly in the comment saying that Claude says to ignore it, but we want to keep dependencies pinned.
    - I think that the terraform .gitignore is really bad as of right now?

## 2025-07-28

Been busy elsewhere. Luckily I have this helpful little lab notebook to see what I was working on at the time. 

Biggest thing that we're facing is trying to deploy our code to our test environment. We ran into issues with the worktree git setup (which I still like, and in fact like more that we've run into these issues -- it functions kind of like CI/CD in that you need to pre-emptively solve "well it works on my machine" issues). We solved the first issue, of uv not installing our package as an editable install, but we still need to solve the issue of terraform not syncing our files down properly. One issue we're going to have is that the clean way for this to happen would be the state file being added to our git repo in the master branch, but we're going to be adding it into our dev branch instead. This might cause annoyance when we go to merge our branch in, but we'll deal with it when we get there.

Once we deploy our code, we still need to do the core thing we wanted to, which is testing the POST requests. We already expect there to be an issue with the lease_id being the wrong type (a string instead of an int), and thus comparing wrong in SQLite. 

So, starting off, let's update the goals doc

Okay, now let's determine what the correct .gitignore for terraform is

https://stackoverflow.com/questions/66080465/gitignore-file-for-terraform
- Recommends a certain set of files, not including the state file, for ignoring -- possible.
    - Ignore variable files (valid? should this be a machine by machine thing?)
    - Ignore override directory (valid? I guess this could be used to override specific things for your machine, but I would want to use overrides moreso for modules / reusability)
    - Ignore environment specific file (valid, might contain secrets / be specific to the local machine)
    - Ignore CLI config files (valid? I'm not actually sure what these do...)

https://developer.hashicorp.com/terraform/cli/config/config-file
- Yeah, this all seems like things that are machine specific

https://spacelift.io/blog/terraform-gitignore
- Hmm, they recommend ignoring state files, because they update every plan and apply... Every plan and apply? Or just ones that made changes?
- Ignore crash logs too -- I like that
- Ignore .pem, .pub, .key -- no, this is dumb, don't store your keys in the project, also while it would be weird to commit your .pub file, it's not a secret...
- They say "# Exclude all .tfvars files, which are likely to contain sensitive data, such as password, private keys, and other secrets. These should not be part of version control as they are data points which are potentially sensitive and subject to change depending on the environment."
    - Interesting -- vars file vs environment file for secrets?
- Wait, they call out ignoring environment files earlier, and then don't put it into the final file output... is this AI slop, or just bad? Also, actually, they call out ignoring environment file, but that's actually just a .envrc file, that's not terraform specific at all (I think it's direnv?). Dumb.
- I'm reserving judgement, but I might stop reading spacelift.io for information, they don't seem trustworthy

https://spacelift.io/blog/terraform-secrets
- "Terraform uses secrets to automate infrastructure provisioning activities similar to the ones listed above. The secrets are also stored/managed in state files referenced by Terraform for its workflow."
    - Uhhhh wait secrets are in state files, this is something important -- is this real? We're already not sure if we trust spacelift.io...
        - https://developer.hashicorp.com/terraform/language/state
            - Recommend storing it in the Terraform proprietary version control...
            - Nothing about secrets, but we can also go check it out, it's just JSON
        - It looks like variables are stored there, so could definitely see secrets being there -- there's also an array for "sensitive_attributes", maybe there's functionality to hide certain things from the state file?
        - https://developer.hashicorp.com/terraform/language/state/sensitive-data
            - "Terraform state can contain sensitive data, depending on the resources in use and your definition of "sensitive." Unless your variables or resources are ephemeral, the state contains resource IDs and all resource attributes. For resources such as databases, this can contain initial passwords."
            - Okay, it's valid that you wouldn't want resource IDs public, and resource attributes too. Initial passwords would be not great to publish. 
            - "You can also mark your sensitive data in variables as ephemeral to prevent Terraform from writing those variables to your state and plan files."
                - This seems like the way -- avoids most of the actual sensitive data making it into the state file
            - In an actual company, using remote state seems the best -- avoids needing to commit the state files, keeps everyone in sync with the actual real state (not just whatever they last used locally), and makes it cleaner when releasing code publicly (because the public doesn't need to spin up like a new dev on the team, they don't need or want internal company state files)

https://developer.hashicorp.com/terraform/language/ephemeral
- Hmm. I don't think I fully understand how to use this, but I'll try once we get to the point of needing secrets

https://old.reddit.com/r/devops/comments/10a7j78/terraform_how_do_you_handle_secrets/
- I'm really coming around to "there's no way to make the state file safe", and that we need to just treat it as toxic and avoid committing it.
- So my issue then changes -- how do you spin up a new dev on a project with existing resources? It's not commiting the state file, that's a breach waiting to happen, is there another command to make terraform generate a new state file off existing resources?

https://support.hashicorp.com/hc/en-us/articles/4403065345555-Terraform-State-Restoration-Overview
- Just how to fix a bad state file, not how to regenerate one (is the state file the only way to connect logical resources to real ones? It's very possible, if terraform doesn't apply some marker of its existence onto every resource. Honestly, that's kinda likely too)

https://developer.hashicorp.com/terraform/tutorials/state/refresh
- `-refresh-only` flag for plan and apply allows some reconciling of state
- Doesn't mention making entire state files up from existing resources

https://stackoverflow.com/questions/74205524/how-to-recover-terraform-state-file
- Yeah, it's for Azure but I assume it's the same for AWS -- there might be ways to recover the state file, but they aren't easy or clean.

Okay, so we're at
- We need the state file to spin up new devs
- But the state file can't be part of our git repo
Thus:
- We need to have an out of band process to spin up the dev

This probably looks like the remote backend that Terraform talks about in their docs. Goodness, I'm starting to like this tool less.

Okay, so remote backend is one option. Another option is doing stupid copy and paste (at least for me as a solo dev) -- I
This probably looks like the remote backend that Terraform talks about in their docs. Goodness, I'm starting to like this tool less.

Okay, so 
- remote backend is one option. 
- Another option is doing stupid copy and paste (at least for me as a solo dev)
    - I like this less -- I'd prefer to do the right thing, and the thing that will teach me more about the tool
- committing the state file is _not_ an option -- it's a reasonable thing right now, but it's a loaded gun pointed at our foot the moment we want to add auth and etc
- Rolling our own remote backend (using probably S3 and a poe task that updates the state as part of our apply / plan) honestly doesn't sound the worst, but I bet that's basically what the real remote backend does, and we don't have to continue to support it after the fact
- Do whatever the annoying and difficult process is to update state file from existing resources -- this is honestly my favorite, but I feel like this would be intended behavior if it worked in all cases.    
    - Very "crash-first" design
    - Would mean that the state file is just a helpful cache, but I think it's doing more than that

https://medium.com/@abtreece/recovering-terraform-state-69c9966db71e
- Talks about recovering state using the import command
- Yeah, this is gross and disgusting -- good if I needed to import a single resource, but no more

Okay, remote backend it is

https://developer.hashicorp.com/terraform/language/backend
- Backend block in the tf.main file
- Default backend is `local` -- I guess it's all an interface, wonder how that plugin system works
- Recommend using environment variables to specify creds
    - Should be fine, aws cli should take care of this for us?
- Rerun `terraform init` when updating the backend

https://developer.hashicorp.com/terraform/language/backend/s3
- Use Bucket Versioning in real-use
    - This will use a lot more space, sooooooo I think we're going to not do that for this project

https://developer.hashicorp.com/terraform/language/state/workspaces
- Workspaces?
- Requires using a backend that supports workspaces (like S3)
- https://developer.hashicorp.com/terraform/cli/workspaces
    - Select the workspace in use via the CLI -- not by directory
    - Different state files

Okay. We're going to create a bucket for this, and use the provided sample backend config. Should be easy enough, hopefully the aws cli just makes the credentialing work

Put in the backend line into both the worktree and into master -- we're going to run the terraform init from master to hopefully push the state file up, and then be able to use it in the worktree

Running in master success, asked us to copy up state file to backend, we said yes, created a state file in our bucket.

Weird error trying to run `tf plan` in worktree -- `An argument named "triggers_replace" is not expected here.` on data.archive_file.lambda_source
    - Why are we only seeing this error now? This shouldn't have changed since last run
    - Or has it changed, and we've been bad about not pushing up changes after we make them?
    - OOOOOHHHH, we did change it, actually recently -- so that it'll replace properly. Was this what we were doing right before we ran into this deploy problem?
        - We didn't talk about it in the notebook...
        - This looks like we pulled it from somewhere

https://stackoverflow.com/questions/51138667/can-terraform-watch-a-directory-for-changes
- This looks to be where I pulled it from
- Not a triggers_replace, but a triggers, and on a null_resource (the old implementation of a data resource)
- Do we need this though? This feels like an old kludge, that I would hope is improved by now

https://registry.terraform.io/providers/hashicorp/archive/latest/docs/data-sources/file
- I would expect this to just work...
- Since I didn't write anything about this, I'm going to just remove these changes and see what happens


Failed to find any changes... Hmm, okay, I bet that this is why I found that article

## 2025-07-29

Checking the zip file in the build folder, however, looks like the app.py is correct -- I think it's just a matter of it created the zip file in the past and hasn't needed to update it yet. 

I'm going to try to deploy and see what happens.

We needed to run tf init in the worktree as well -- we are using the state file from s3 (this is a mistake... I've done updates in the worktree to the function that we'd like to retain)

Running tf plan, we only see updates needed on the zip files and the lambda function, which is great -- nothing was too far off.

Going to run my apply, and then be able to test!

Complete! Testing now, finally

Internal Server Error! Yay! Checking logs

Issue is Jinja isn't finding the package. Is this due to our earlier updates, when we were making testing work? We've now progressed to "it works on my machine" yet again.

I'm going to check around the Jinja code, just visually look at it

Yep, error at that point. We were hoping that Jinja would be doing exactly the same thing we were doing with the importlib resources, but it seems to be slightly different (at least given the fact that we saw the error here, and not earlier when we were doing the other imports). I'm going to check the Jinja docs to see what I should be doing here (honestly, I'm a little confused at what PackageLoader is even doing -- should I be using just a `.` for a relative import instead? I'm going to check this notebook before diving into the docs, see if I can understand what I knew before).

It doesn't look like I've written anything about the Jinja PackageLoader in here. I'm going to the docs

Docs weren't super helpful -- PackageLoader loads the package, you pass it a package name. This package is used to find the template resources in the templates folder. `.` as the package name doesn't seem to be excluded from possibility?

Using `.` as a package name seems to not 100% break things -- running `poe test` didn't fail, but I don't think we're actually going through that code block with tests right now.

Let me write a quick and stupid test for the `/` path

Okay, we failed, looks like the sqlite database is not set up correctly -- we're having an error that there's no table "Lease". Probably something in our fixture code?

Not seeing anything obvious -- going to add some print calls into the tests, see if that throws anything up, and then see if pytest has a way for us to drop into the offending test in a shell to see what's going on (is the path wrong? Does the db not exist? Is the fixture not setting it up correctly?)

prints make it look like the database exists, maybe doesn't have data? But that shouldn't matter. Going to look for a way to drop into a shell from pytest -- my expectation is that for some reason, the database doesn't have the structure we wanted to create with our ddl.

https://stackoverflow.com/questions/19169402/nose-or-pytest-drop-in-to-interactive-console-when-running-tests
- It looks like I can use `pytest.set_trace()` to drop into an interactive shell
- Except the docs linked are old, and going to the latest is different? Also, they don't say that anyway?

https://docs.pytest.org/en/6.2.x/usage.html
- This seems to say that using pytest --trace will drop into pdb at the start of each test
- But we don't want that, I just want to drop into pdb (really ipdb) when it fails...

I'm going to try to just put a breakpoint in and see what happens -- might be an issue with poe if the test task isn't set up to run inside the same process, but we'll see

Complaining -- it thinks we should be using pytest -s when trying to read from stdin while output is being captured

Lets try to run the pytest command from poe with -s

Hmm -- the poe test task we made is using ISLOCAL=':memory:', which is not what we want -- we're setting ISLOCAL with our monkeypatch, but that's interesting, I wonder if there's an effect

Trying to run pytest is giving errors because we don't have it installed as a tool, so bash is erroring. Is poe able to run it because it's uv conscious? How does uv tool work?

`uv tool run pytest -s` perhaps

............ did uv uninstall our editable install again? It installed pytest (weird, why did that happen? Clearly poe is using something slightly different), but then pytest failed saying it can't import rent_app

We did see that rent_app got changed in the last uv install, but I figured that wasn't an issue.

I see rent_app in the site_packages folder in the venv... Why isn't pytest seeing it?

I'm going to test with a uv python shell, see if I can import rent_app
- we run a uv python shell with `uv run python`

I can import it -- it's just an issue with the tool use, then?

That aligns -- the tool is venv agnostic, we actually need to run the python in the venv -- we could probably do this with `uv run python -m -- pytest -s .`, but that seems... overwrought

https://docs.astral.sh/uv/pip/environments/
- Specifically pip, we don't really care about this

https://github.com/astral-sh/uv/issues/11472
https://docs.astral.sh/uv/concepts/tools/#relationship-to-uv-run
- I think I want uv run?

Going to try `$ ISLOCAL=':memory:' STAGE=prod uv run pytest -s`

ayyyyy it worked!

Okay! ISLOCAL did not get changed. That's weird, but at least we can work with it

We're definitely setting ISLOCAL -- print statements in the tests are working correctly, showing that it's the path

This is real confusing -- everything in the testing script looks like we're correctly setting the environment, it's just not passing down to the app. Going to see if this is a known issue

https://stackoverflow.com/questions/73569566/pytest-monkeypatch-not-overruling-environ-variable
- Ah. Yeah, that makes sense, we're importing environ too early, before our monkeypatch can take effect, ~~and then the environ dict doesn't get mutated by the changes~~ (correction 2025-07-30 -- we're storing the value in ISLOCAL, I... believe the dict would be mutated? Let me check. It doesn't! iiiiiinteresting)

So, what does that leave us with? Change to importing environ inside the actual function (I don't like it, cleaner to have ti at the top); monkeypatch the constant instead of the environment (maybe, but means we're not testing the environment variable selection process); "mock environment in pytest_sessionstart" -- maybe this? I'm not sure where this is, have to do more reading; keep digging

https://docs.pytest.org/en/stable/how-to/monkeypatch.html

## 2025-07-30

Okay, continuing to dig on monkeypatching. My expectation is that I'll need to use the sessionstart, but it's also possible that I should make my design more amenable to testing. Due to finding that the environ dict doesn't mutate, I think changing the design would be more in-depth than a single easy replacement (e.g. just referencing the environ dict directly vs defining a constant), so I'm less interested in that. I'll look deeper into the pytest_sessionstart

I should also check to make sure my db is going to test correctly -- we're not reconnecting every time, and I doubt that pytest is reimporting the package fresh every time (so our connection will be reused). I need to check whether we're overwriting the original db, or if we're using a new path every time (I think it's the second), and whether we're reimporting the package fresh each test run (I doubt it).

In order to check this, I'm going to take a look at the code, and then I'll put a print in the main body of the rent_app module -- if it gets reimported, it'll run twice, otherwise it'll only print once. 

Pytest only shows the prints from the tests if they fail... Okay, so that's a no-go. Let's start with one crisis at a time, fix this erroring test, and then we can use the tests to test the testing harness

Cleaning up the changes, then going to continue research

https://stackoverflow.com/questions/16924471/difference-between-os-getenv-and-os-environ-get
https://stackoverflow.com/questions/10952507/when-would-os-environfoo-not-match-os-getenvfoo
https://www.florianreinhard.de/python-environment-variables/
- Noticed that the monkeypatch docs were using os.getenv, and were doing tests in a way that looked like they were expecting to be able to see changes to environment variables between tests -- I wondered whether this meant that os.getenv gets directly from the environment variables, where os.environ is unmutated after instantiation. However, it seems this isn't the case -- os.getenv is just a wrapper around os.environ.get
- So this is evidence for the idea that the environment is wiped clean and all imports are re-run between tests, or more likely that monkeypatch works on the Python level, rather than just at the os level. So changing my code to just check the environment when I need the db path would probably do it (the simple and easy method)

https://docs.pytest.org/en/stable/reference/reference.html
- Okay, it's a hook -- how use?

https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html
https://pytest-with-eric.com/hooks/pytest-sessionstart-sessionfinish/
- Hmm, what exactly is a pytest "Session"?
- Recommends using a conftest.py file -- necessary? I might do it anyway, we're gonna want the db connections across any of our test files
- https://pytest-with-eric.com/pytest-advanced/pytest-addoption/
    - Add CLI options to pytest in the middle of a run? This could be the easy way to add -s when I want to be able to do ipdb

Easy enough, it looks like -- we're going to create a conftest file with the environment and db setup, and then proceed from there

Can hook implementations be fixtures? I wonder how it's done under the hood...

It'd be a terrible name for the fixture -- I'm going to do a quick search, and if it's inconclusive, finish this up and do some testing once it works

https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html
- Looks like conftest.py and plugins are the only places you can declare hooks -- but this doesn't say whether this includes hook implemenations as well (just new optional hooks)

https://stackoverflow.com/questions/55413277/can-pytest-hooks-use-fixtures
- I'm a little concerned that the default fixtures (monkeypatch etc) won't work in the hook, which would be tough and annoying

https://pytest-with-eric.com/hooks/pytest-hooks/
- This says you can define hook implementations outside of conftest.py

Okay, I found nothing, just going to continue making things work and check if there's a better way after

Testing, can't use monkeypatch normally -- let me see if there's a way to use fixtures in hooks, or if we're just going to do some raw editing (reasonable), and need to figure out our own tmp_path (harder?)

https://github.com/pytest-dev/pytest/issues/5012
- Okay, big no

Okay, so monkeypatch I don't need -- I can just change the environment myself. But doing up a temporary path? That's a bit trickier, because I want to make sure it's unique, and not going to muddle between test runs. Maybe I can just call a pytest function directly to get a temp path?

https://docs.pytest.org/en/stable/how-to/tmp_path.html
https://stackoverflow.com/questions/36070031/creating-a-temporary-directory-in-pytest
- It looks like I could do something dumb by accessing the underlying way that pytest creates temp dirs, but that seems silly, too much, and liable to break

I think that I'm going to need to just make my own temporary file in the /tmp directory -- this isn't great, means that my tests aren't portable to windows (were they anyway? I don't really know how pytest works), but I can't use the pytest temp dir creation. When does the base python temp path creation do cleanup? Does it clean its own files up, or just let the os do that?

https://docs.python.org/3/library/tempfile.html
- We want to use mkstemp, and then delete in a sessionstop hook -- if we fail to delete it, we don't really care, we aren't using this for security, we're just avoiding storing unnecessary data / making sure we have a clean working environment

Plan in place -- we're going to use mkstemp from the stdlib tempfile package, and add an additional hook impl that deletes the file

Cool, that seems to be reasonable -- we're now getting a new error in our test! Jinja doesn't like our "." anymore it looks like?
- Ahhh yeah last time we didn't actually make it there, so this is the first time we're testing it

https://stackoverflow.com/questions/8512677/how-to-include-a-template-with-relative-path-in-jinja2
https://pwan.org/blog/an-exploration-into-jinja2-unit-tests-wth-pytest.html
- Hmmmm this guy seems to be mocking out a lot of jinja stuff

https://stackoverflow.com/questions/75160109/python3-and-pytest-jinja2-exceptions-templatenotfound

Hmm. Maybe I can load using something other than the package loader? I don't feel like I fully understand the Jinja Environment right now

So, let me just lay out what I believe is happening here:
- We're using the PackageLoader in Jinja to load our templates
- This uses an imported pacakge (or otherwise importable target, such as the name of a python file on the PYTHONPATH) as the base to find the templates
- Locally, we install the package and run from its name (rent_app)
- However, on Lambda the runner is just importing from local context -- directly running the app.lambda_handler function

This suggests a solution -- instead of using local context, we instead have the module in a package named "rent_app" that we then run from local context.

We can achieve this by packaging our app one level higher -- instead of packaging at src/rent_app/, we package at src/, leaving us with just a top-level directory rent_app (perfect)

This is a new project. I want to make a project.md or similar to really nail down what my goals are here.
My goal is for this project to be learning how to work with AI to both make my skills grow as well as t learn how to use AI better.
This project should be more about learning than it is just trying to get the project out the door, if I don't learn new informationabout the tools I am using as the project progresses then I have failed.

Project summary: I want to write a series of scripts and tooling to decompile super auto pets and then create sort of like a quick wiki but more for data specific stuff. My goal is to fully host this because I need to learn how to do the fullstack + devops pipeline.

The product phase will be important to help analyze what we are actually developing. As we go through all the phases (in the future)we wil need to store the results of each phase so we can easily reference it later.

Learning Notes:
1: I would like to better learn typescript as part of this process
2: I have started learning Drizzle a little bit at work, idk if its what I want to use but maybe, should be part of the product phase discussions.
3: I know almost nothing about devops so a lot of this is going to be trial by fire and asking a lot of AI questions.
4: I want to learn how to better utilize context management strategies for AI so that I can get better results in my professional endeavours.

Product Phases:
0: During this entire process everything the human learns needs to be properly documented so that I can reference it later and potentially update my resume.
1: Do some discovery and discussion to determine what data we want the end user to be able to see from the decompiled game.
2: What kind of UX do we want?
3: What kind of features should the site have?
4: Figure out where we want to host and run the code, what is the pricing going to look like?
5: Figure out what kind of tooling we want to use for CI/CD.
6: Figure out what reverse proxy we want to use.
7: We probably are going to use something like Railway or render since this is my first time doing this and my goal is to learn.
8: Ideally we can pull everything from the game files, but if absolutely needed we can try to use the wiki.gg sources api.php to pull some stuff off the wiki, this will reduce accuracy tho.
9: When a new game version drops and my stuff updates there should be a changelog based on our decompiled results and not based on any other changelog information.
10: Having a pack builder where multiple people could edit the same pack (like a webhook lobby type of system) would be huge so I can make a pack with my boyfriend and we are both on our phones.
11: What DB infrastructure do I want to use?

AI Design:
1: We have an underlying goal that when AI does things we want it to build IN as much of the existing stuff as possible and when it builds ON it it is expanding the functionality and not just piling shit up, to do this we need super solid evals, tests, standards, skills, claude.md files, and commands to really nail this.

Tooling Phases:
1: Linting should exist for everything, linting will help us keep consistent.
2: Testing should exist for all of this (that includes end to end tests with playwright or similar)

Development Phases:
0: Write up a dockerfile to create a docker container for running this entire project. (Future phases will note the tooling we want)
1: Write scripts to pull game files, decompile them, and store the specific pieces of data I want for display purposes later. We are likely to do this in the docker container so I don't have to download all the tooling onto my system for it to sit around on.
2: Create an API layer (backend) using NodeJS in order to be able to serve pet data to consumers. As part of this I need to setup postman and be able to actually pull the data. We will likely want to use Swagger or equivalent for an easy to use visualization of the APIs. If it is possible to visualize the API through postman that would also be interesting to experiment with.
3: Create the frontend that can actually digest the API and show it to consumers. This is where I specialize so I should spend minimal time here beyond learning how to better interact with the AI.
4: Setup a super solid error logging system so we can easily monitor what is happening and where things are breaking for simple fixes later. This system has to be fully usable and readable by both humans (me) and AI. I should be able to do some kind of setup to alert me on my phone in real time through some mechanism because this is what would be needed in the real world.
5: Create some CronJobs that can run to re-grab the game (once a week or something, or on the fly when I trigger something) and decompile it to update our sources. This will be needed so we can grab updates anytime a patch drops. As part of this we should check to see if the game has a new version and if it doesn't we can skip the decompile phase.
6: Setup redis for redis reasons.
7: Setup websockets to monitor active users as well as drop notifications when needed (such as when a new patch drops).
8: Setup an MCP server so that an AI could communicate with this new site since thats a hot skill on resumes right now.

Frontend Design Phases:
1: Once it is time to build the frontend we want to see if we can make a fully accessible design system with css variables as quickly as possible.
2: After that we want to utilize the design to make all the stuff we determined we want the user to be able to do.

Long Term Phases:
1: Move from Railway or Render to a VPS for more learning.
2: Finally learn Terraform for even further learning.

Note to my AI friend reading this:
For this task I am fully aware all of these are a bit intense and verbose for the final product, but the goal is to learn and grow as a human and professionally.


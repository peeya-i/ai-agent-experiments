The following prompts were provided to Antigravity IDE with Gemini 3.7 Medium model:
- **Prompt:**
Create an ML grader app that accepts the student name and folder name, then evaluates whether the app in the folder works as described in the SPECIFICATIONS.md file in the folder. The result should be a score showing how well the app matches the information described in the specification. The app should store the name and score of each student for each submission using a single line json format in the file called scores.json.
There should be an instructor view to show the list of students with the highest score and the latest submission of each student. When the name of each student is clicked, the app will show all the submissions from that student.
Implement this in python.

- **Prompt:** Create a README.md showing how to start and use the application

- **Prompt:** Change the code to load the API key and the model name from the .env file

- **Prompt:** What caused this 404 Not Found and how to fix it?

- **Prompt:** What caused this problem and how to fix it:
Warning: LLM evaluation with model 'gemini-3.5-flash' failed (HTTPSConnectionPool(host='generativelanguage.googleapis.com', port=443): Read timed out. (read timeout=60)), falling back to intelligent heuristic engine.

- **Prompt:** The specification in this folder "/home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder" includes a request for logging user input in CSV format, but the code was not completed. Why is the score still 100%? Why is the gap not count as a reduction in the score.

- **Prompt:** Why the Score was 100% when the implementation is incomplete.

- **Prompt:** Added the following scoring distribution

- **Prompt:** Update the scoring distribution based on the information in SCORING.md file.

- **Prompt:** For each scoring criteria, provide more details about the reasons for the score, especially if it is not a perfect score.

- **Prompt:** Can the LLM calls programmed to retry until it can be completed?
Added retries and progressive back-off delay for each try.

- **Prompt:** If the app can't call the model, display a message that the grader is not available at this time. Don't print a heuristic engine.

- **Prompt:** Add the name of the model used to evaluate the grade in the output. Add the ability for the student to download the analysis in pdf or text format.

- **Prompt:** The app didn't properly complete the PDF download. The file name was /Downloads/Unconfirmed 877624.crdownload

- **Prompt:** Change the code to get the specs from SPECIFICATION.md, SPECIFICATIONS.md, SPEC.md, SPECS.md, or similar files in both upper or lower case.

- **Prompt:** Why would the code provide this feedback asking about trip planner when the app is not about trip planner:  The application is a weather dashboard rather than an iterative trip planner, so there is no Scheduler reading critic_feedback from prior iterations to modify a trip.
The following is the repository: https://github.com/vijayrgopu/agent_engineering/tree/main
The folder where the app is located: my-work/my-app

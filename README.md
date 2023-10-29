# Description
Command line tool that combines the power of ChatGPT with your Confluence Wiki to create a chatbot that knows your internal documentation

# Installation
Requirements
* Docker must be installed on your system
* you need a Confluence instance in the cloud and a personal API token (PAT) for remote access to the contents of your wiki
* last but not least, you need an OpenAI account with a credit balance

Once these requirements are met, you are ready to go. The installation is done in four simple steps:

**1. ️Clone the Repository**
Clone the repo to a local directory.
```cmd
git clone https://github.com/dirk-weimar/confluence-chatbot
 ```

**2. Create Dockerfile**
Create a file named Dockerfile with the following content in the root directory of the app:
```cmd
# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV OPENAI_API_KEY 'your-openai-api-key'
ENV CONFLUENCE_URL 'your-confluence-url'
ENV CONFLUENCE_USERNAME 'your-confluence-username'
ENV CONFLUENCE_API_TOKEN 'your-confluence-api-key'

# Define the standard acrion
ENV ACTION 'start-chatbot'

# Run app.py when the container launches
CMD ["python", "app.py"]
```

**3. Configuration**
Populate the environment variables in the Dockerfile you just created with your real connection data for Confluence and OpenAI.
In the app.py file, set the range keys of the Confluence spaces you want to use. You can specify one or more spaces.
```cmd
confluence_spaces = ['TST', 'SYS']
 ```

**4. Building the app**
Change to the root directory and build the app locally using Docker.
cd confluence-chatbot
```cmd
docker build -t confluence-chatbot .
```

# Running the App
Now you're ready to import your data from Confluence. Start the app with the ACTION "collect-data":

```cmd
docker run -it --rm -v $(pwd):/app -e ACTION=collect-data confluence-chatbot

# output
Load information from the Confluence space TST ...
44 pages loaded -> split into 47 pages
Add embeddings ...............................................
CSV file data/pages_data_TST.csv written
```

Your chatbot is ready to go. Start it (without the ACTION parameter this time) and ask it questions that require specialized knowledge from your wiki to answer:
```cmd
docker run -it --rm -v $(pwd):/app confluence-chatbot
```

To exit the app, type "exit" into the console instead of a question and confirm with Enter.

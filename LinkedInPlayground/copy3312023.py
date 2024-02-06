from selenium import webdriver
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import json
import requests
from selenium.webdriver.chrome.options import Options
import openai
import os

openai.api_key = os.environ.get('OPENAI_API_KEY')

def search_linkedin():
    # Prompt the user for a search query
    query = input("Enter a name and organization (e.g. Bill Gates Microsoft): ")

    # Perform a Google search for the query
    url = f"https://www.google.com/search?q={query}+site:linkedin.com"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
    response = requests.get(url, headers=headers)

    # Extract the URLs of the top 5 LinkedIn results
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("div", class_="g")
    linkedin_urls = []
    for result in results:
        link = result.find("a")
        if link and "linkedin.com" in link["href"]:
            linkedin_urls.append(link["href"])
        if len(linkedin_urls) == 5:
            break

    # Prompt the user to select a LinkedIn result
    for i, url in enumerate(linkedin_urls):
        print(f"{i+1}. {url}")
    print("Select a LinkedIn profile: ", end="")
    selection = int(input()) - 1


    # Return the URL of the selected LinkedIn result
    return linkedin_urls[selection]



def scrape_linkedin_profile(url):
    # Set up Chrome webdriver options
    options = Options()
    options.add_argument("--headless")  # run Chrome in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Start the Chrome webdriver and open the LinkedIn profile URL
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    # Scroll to the bottom of the page to load all elements
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Get the page source and close the webdriver
    html = driver.page_source
    driver.quit()

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Find the script tag containing the JSON-LD data
    script = soup.find('script', {'type': 'application/ld+json'})
    if script is not None:
        # Parse the JSON data
        data = json.loads(script.text)

        # Extract the fields of interest from the JSON data
        person = data['@graph'][0]

        name = person.get('name', '')
        job_title = person.get('jobTitle', '')
        current_company = person.get('worksFor', [])
        current_company_name = [org.get('name', '') for org in current_company]
        location = person.get('address', {}).get('addressLocality', '')
        education = []
        if 'alumniOf' in person:
            previous_jobs = []
            for school in person['alumniOf']:
                #This is how schooling is stored in the alumniOf object
                if 'EducationalOrganization' in school.get('@type'):
                    education.append(school.get('name', ''))
                #This is how previous jobs are stored in the alumniOf object
                elif 'Organization' in school.get('@type'):
                    previous_jobs.append(school.get('name', ''))
            education_str = ', '.join(education) if education else ''
            previous_jobs_str = ', '.join(previous_jobs) if previous_jobs else ''
        else:
            education_str = ''
            previous_jobs_str = ''

        # Extract the 'About' text from the page source
        about_text = ''
        about_section = soup.find('meta', {'name': 'description'})
        if about_section is not None:
            about_text = about_section['content']

            # Remove the LinkedIn profile information at the end of the about section
            linkedin_info = "| Learn more about"
            if linkedin_info in about_text:
                linkedin_index = about_text.find(linkedin_info)
                about_text = about_text[:linkedin_index].strip()

            # Remove the default about section if one is not present originally
            profile_info = "View"
            if profile_info in about_text:
                profile_index = about_text.find(profile_info)
                about_text = about_text[:profile_index].strip()

        # Create a dictionary to hold the data
        profile_data = {
            'name': name,
            'job_title': job_title,
            'current_company_name': current_company_name,
            'location': location,
            'education': education_str,
            'previous_jobs': previous_jobs_str,
            'about': about_text,
            'url': url
        }

        # Add the data to MongoDB
        client = MongoClient()
        db = client['mydatabase']
        collection = db['mycollection']
        collection.insert_one(profile_data)

        print(f"Added {name} to MongoDB.")
        print()
        print("Here's the data that was scraped:")
        print(f"Job Title: {job_title}")
        print(f"Current Company: {current_company_name}")
        print(f"Location: {location}")
        print(f"Education: {education_str}")
        print(f"Previous Jobs: {previous_jobs_str}")
        print(f"About: {about_text}")
        print(f"URL: {url}")
        print()

        return profile_data



def write_email(profile_data):
    # Prompt the user to choose which variables they want to use in their email
    print("Which variables would you like to include in your email?")
    print("1. Job Title")
    print("2. Current Company")
    print("3. Location")
    print("4. Education")
    print("5. Previous Jobs")
    print("6. About")
    choices = input("Enter the numbers of the variables you want to include separated by commas: ")
    choices = [int(choice.strip()) for choice in choices.split(',')]

    # Get the selected variables from the profile data
    variables = []
    for choice in choices:
        if choice == 1:
            variables.append(profile_data.get('job_title', ''))
        elif choice == 2:
            variables.append(', '.join(profile_data.get('current_company_name', [])))
        elif choice == 3:
            variables.append(profile_data.get('location', ''))
        elif choice == 4:
            variables.append(profile_data.get('education', ''))
        elif choice == 5:
            variables.append(profile_data.get('previous_jobs', ''))
        elif choice == 6:
            variables.append(profile_data.get('about', ''))

    # Prompt the user to enter the temperature they would like to use
    temperature = float(input("Enter the temperature you would like to use for the email (e.g. 0.5): "))

    # Prompt the user to enter what type of email they'd like to make
    #email_type = input("Enter in what you would like to ask the target to join based off the information (e.g. inviting them to a research opportunity): ")

    # Generate the email using OpenAI API
    prompt = f"Write an email to {profile_data.get('name', '')} inviting them to a research opportunity, sign off the email with a random name, and embed this link 'www.stetson.edu'; here's some information about {profile_data.get('name', '')}:\n"

    # Failed idea
    #prompt = f"Write an email to {profile_data.get('name', '')}" + email_type + " and embed a link; here's some information about {profile_data.get('name', '')}:\n"

    for variable in variables:
        prompt += f"- {variable}\n"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=temperature,
    )

    print()
    print(prompt)
    # Print the generated email
    print("Here's the email that was generated:")
    print(response.choices[0].text)

    client = MongoClient()
    db = client['mydatabase']
    collection = db['emailinformation']

    # Create a dictionary with the data to be inserted
    email_data = {
        'variables': variables,
        'temperature': temperature,
        'prompt': prompt,
        'response': response.choices[0].text
    }

    # Insert the data into the collection
    collection.insert_one(email_data)


if __name__ == '__main__':
    selected_profile = search_linkedin()
    print("Your selected profile is: " + selected_profile)
    data = scrape_linkedin_profile(selected_profile)
    write_email(data)

# Import necessary libraries
from selenium import webdriver
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import json
import requests
from selenium.webdriver.chrome.options import Options
import openai
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Set OpenAI API key from environment variables
openai.api_key = os.environ.get('OPENAI_API_KEY')

def search_linkedin():
    """
    Prompts the user for a search query, performs a Google search,
    and allows the user to select a LinkedIn profile from the search results.
    """
    # Prompt the user for a search query
    query = input("Enter a name and organization (e.g. Bill Gates Microsoft): ")

    # Perform a Google search for the query
    url = f"https://www.google.com/search?q={query}+site:linkedin.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Extract the URLs of the top 5 LinkedIn results
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("div", class_="g")
    linkedin_urls = []
    for result in results[:5]:  # Limit to top 5 results
        link = result.find("a")
        if link and "linkedin.com" in link["href"]:
            linkedin_urls.append(link["href"])

    # Prompt the user to select a LinkedIn result
    for i, url in enumerate(linkedin_urls):
        print(f"{i+1}. {url}")
    selection = int(input("Select a LinkedIn profile: ")) - 1

    # Return the URL of the selected LinkedIn result
    return linkedin_urls[selection]

def scrape_linkedin_profile(url):
    """
    Scrapes the LinkedIn profile using Selenium and BeautifulSoup to extract
    key information and stores it in a MongoDB database.
    """
    # Set up Chrome webdriver options
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
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

    # Extract profile information from the HTML
    script = soup.find('script', {'type': 'application/ld+json'})
    data = json.loads(script.text) if script else {}
    person = data.get('@graph', [{}])[0]

    # Create a dictionary to hold the scraped data
    profile_data = {
        'name': person.get('name', ''),
        'job_title': person.get('jobTitle', ''),
        'current_company_name': [org.get('name', '') for org in person.get('worksFor', [])],
        'location': person.get('address', {}).get('addressLocality', ''),
        'education': ', '.join([school.get('name', '') for school in person.get('alumniOf', []) if 'EducationalOrganization' in school.get('@type', '')]),
        'previous_jobs': ', '.join([job.get('name', '') for job in person.get('alumniOf', []) if 'Organization' in job.get('@type', '')]),
        'about': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
        'url': url
    }

    # Add the data to MongoDB
    client = MongoClient()
    db = client['linkedin_profiles']
    collection = db['profiles']
    collection.insert_one(profile_data)

    print(f"Added {profile_data['name']} to MongoDB.")

    return profile_data

def write_email_gui(profile_data):
    """
    Creates a GUI using Tkinter for the user to customize the email content
    based on the scraped LinkedIn profile data and generate the email using OpenAI's GPT-4.
    """
    # Create the main window
    window = tk.Tk()
    window.title("Email Customization")

    # Checkbox states for selecting profile information
    var_job_title = tk.BooleanVar(value=True)  # Default: include job title
    var_current_company = tk.BooleanVar(value=True)  # Default: include current company
    var_location = tk.BooleanVar()
    var_education = tk.BooleanVar()
    var_previous_jobs = tk.BooleanVar()
    var_about = tk.BooleanVar()

    # Create checkboxes for each piece of profile information
    ttk.Checkbutton(window, text="Job Title", variable=var_job_title).pack(anchor='w')
    ttk.Checkbutton(window, text="Current Company", variable=var_current_company).pack(anchor='w')
    ttk.Checkbutton(window, text="Location", variable=var_location).pack(anchor='w')
    ttk.Checkbutton(window, text="Education", variable=var_education).pack(anchor='w')
    ttk.Checkbutton(window, text="Previous Jobs", variable=var_previous_jobs).pack(anchor='w')
    ttk.Checkbutton(window, text="About", variable=var_about).pack(anchor='w')

    # Slider for adjusting the temperature setting for GPT-4
    ttk.Label(window, text="Temperature Setting:").pack()
    temperature_slider = ttk.Scale(window, from_=0.0, to=1.0, orient='horizontal', resolution=0.1)
    temperature_slider.set(0.5)  # Default temperature
    temperature_slider.pack(fill='x')

    # Function to generate and display the email
    def generate_email():
        # Collect selected variables
        variables = {
            'job_title': var_job_title.get(),
            'current_company_name': var_current_company.get(),
            'location': var_location.get(),
            'education': var_education.get(),
            'previous_jobs': var_previous_jobs.get(),
            'about': var_about.get(),
        }
        temperature = temperature_slider.get()

        # Construct the prompt with selected information
        prompt = f"Write an email to {profile_data.get('name', '')} inviting them to a research opportunity, sign off the email with a random name, and embed this link 'www.stetson.edu'; here's some information about {profile_data.get('name', '')}:\n"
        for key, included in variables.items():
            if included:
                prompt += f"- {profile_data.get(key, '')}\n"

        # Generate the email using OpenAI API
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=1024,
            temperature=temperature,
        )

        # Display the generated email
        messagebox.showinfo("Generated Email", response.choices[0].text)

    # Button to generate and display the email
    ttk.Button(window, text="Generate Email", command=generate_email).pack(pady=10)

    # Start the GUI event loop
    window.mainloop()

if __name__ == '__main__':
    # Main execution flow: search, scrape, and write email with GUI
    selected_profile = search_linkedin()
    print(f"Your selected profile is: {selected_profile}")
    profile_data = scrape_linkedin_profile(selected_profile)
    write_email_gui(profile_data)

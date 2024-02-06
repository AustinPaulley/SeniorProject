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
from tkinter import ttk
import random
import time

mongo_uri = "mongodb+srv://jsnidercurtis:bm8yLzAmoFMWY4mM@cluster0.pjbg6jn.mongodb.net/"

openai.api_key = os.environ.get('OPENAI_API_KEY')

def search_linkedin():
    # Prompt the user to enter their LinkedIn profile URL
    linkedin_url = input("Enter your LinkedIn profile URL: ")

    # Return the entered LinkedIn URL
    return linkedin_url


# Scrapes the LinkedIn profile for information we use for our prompt given our target URL, headless can be changed from True to False in case we find any security measures that need to be bypassed
def scrape_linkedin_profile(url, headless=False):
    # Set up Chrome webdriver options
    options = Options()
    if headless:
        options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Start the Chrome webdriver and open the LinkedIn profile URL
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    # Check if there are any security measures or sign-in prompts
    if "security" in driver.title.lower() or "sign in" in driver.title.lower():
        if "security" in driver.title.lower():
            print("The page seems to have security measures.")
        elif "sign in" in driver.page_source.lower():
            print("The page prompts for signing in.")

        print("Please manually address any issues and press Enter to continue...")

        # Wait for user to press Enter
        input()

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
        person = [x for x in data['@graph'] if x.get('@type') == 'Person'][0]

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
        client = MongoClient(mongo_uri)
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
    print("Choose a group")
    print("1")
    print("2")
    print("3")
    choices = input("Enter the number for the group: ")
    choices = [int(choice.strip()) for choice in choices.split(',')]

    # Get the selected variables from the profile data
    groups = []
    for choice in choices:
        if choice == 1:
            groups.append(profile_data.get('job_title', ''))
            groups.append(', '.join(profile_data.get('current_company_name', [])))
            groups.append(profile_data.get('location', ''))
            groups.append(profile_data.get('education', ''))
            groups.append(profile_data.get('previous_jobs', ''))
            groups.append(profile_data.get('about', ''))
        elif choice == 2:
            groups.append(profile_data.get('job_title', ''))
            groups.append(', '.join(profile_data.get('current_company_name', [])))
            groups.append(profile_data.get('previous_jobs', ''))
        elif choice == 3:
            groups.append(profile_data.get('location', ''))
            groups.append(profile_data.get('education', ''))
            groups.append(profile_data.get('about', ''))

    # Six temps in total
    temps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    random.shuffle(temps)

    # Prompt for the OpenAI API
    prompt = f"Write an email to {profile_data.get('name', '')} inviting them to an opportunity, sign off the email with a random name, and embed this link 'www.stetson.edu'. Please keep it about two paragraphs long at maximum and do not include a subject line.; here's some information about {profile_data.get('name', '')}:"

    for variable in groups:
        prompt += f"- {variable}\n"

    print()
    # print(prompt)

    email_data_list = []

    client = MongoClient(mongo_uri)
    db = client['mydatabase']
    collection = db['emailinformation']

    # Create the main window
    window = tk.Tk()
    window.title("Email Responses")
    window.configure(background="black")

    # Set the size of the window to fit the screen
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window.geometry("{}x{}+0+0".format(screen_width, screen_height))

    # Define the color palette
    light_gray = "#F2F2F2"
    dark_gray = "#444444"
    blue = "#007FFF"

    # Define the style
    style = ttk.Style()
    style.theme_use('default')
    style.configure('TFrame', background=light_gray)
    style.configure('TLabel', background=light_gray, foreground=dark_gray, font=('Arial', 12))
    style.configure('TButton', background=blue, foreground=light_gray, font=('Arial', 12), width=15)
    style.map('TButton', background=[('active', dark_gray)])
    style.configure('TCombobox', background=light_gray, foreground=dark_gray, font=('Arial', 12), width=12)
    style.map('TCombobox', background=[('active', dark_gray)])

    # Create a frame to hold the text widgets
    frame = ttk.Frame(window)
    frame.pack()

    def on_combobox_select(event, email_data_item, combobox):
        # Create a new dictionary object for the email data item
        new_item = email_data_item.copy()

        # Find the index of the dictionary in email_data_list with the matching temperature
        index = next(
            (i for i, d in enumerate(email_data_list) if d['temperature'] == email_data_item['temperature']), None)
        if index is not None:
            # Update the dictionary with the selected number
            new_item['number'] = combobox.get()
            email_data_list[index] = new_item

    # Define a function to insert the data into MongoDB
    def insert_data():
        for email_data_item, combobox in zip(email_data_list, comboboxes):
            # Update the dictionary with the selected number
            email_data_item['number'] = combobox.get()

        # Create a dictionary with the data to be inserted
        email_data = {
            'variables': groups,
            'prompt': prompt,
            'email_data_list': email_data_list
        }

        # Insert the data into the collection
        collection.insert_one(email_data)

    # Create a list to hold the comboboxes
    comboboxes = []

    # Create a frame for each text widget and its combobox in a 3x2 grid
    for i, temp in enumerate(temps):
        row = i // 2  # Place the widget in the appropriate row (dividing by 2 since we want 2 widgets in each row)
        col = i % 2  # Place the widget in the appropriate column

        # Create a frame for each pair of text widget and combobox
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=row, column=col, padx=10, pady=10)  # Use grid for text_frame

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system",
                 "content": "You are an assistant who specializes in writing emails and convincing clients to click a link."},
                {"role": "user",
                 "content": prompt, }
            ],
            max_tokens=1024,
            temperature=temp,
        )

        text_widget = tk.Text(text_frame, height=10, width=120, background=light_gray, foreground=dark_gray)
        email_text = response.choices[0].message["content"]
        text_widget.insert(tk.END, email_text)
        text_widget.insert(tk.END, "\n\n")
        text_widget.pack()  # Use pack for text_widget in text_frame

        # Create the options for the combobox
        combobox_values = [str(j) for j in range(1, 7)]

        # Create the combobox and add it to the frame using pack
        combobox = ttk.Combobox(text_frame, values=combobox_values, width=12)
        combobox.current(0)
        combobox.pack(pady=5)  # Use pack for combobox in text_frame

        # Append the combobox to the list of comboboxes
        comboboxes.append(combobox)

        # Store the temperature, response, and selected number in a dictionary
        email_data_item = {
            'temperature': temp,
            'response': response.choices[0].message['content'],
            'number': combobox.get()  # Initialize with the current selection
        }

        # Append the dictionary to the list of email data items
        email_data_list.append(email_data_item)

        # Bind the combobox to the on_combobox_select function
        combobox.bind("<<ComboboxSelected>>",
                      lambda event, email_data_item=email_data_item, combobox=combobox: on_combobox_select(event,
                                                                                                           email_data_item,
                                                                                                           combobox))

    # Add a button to insert the data into MongoDB
    insert_button = ttk.Button(frame, text="Insert Data", command=insert_data)
    insert_button.grid(row=(len(temps) // 2) + 1, column=0, columnspan=2, padx=10, pady=10)  # Use grid for insert_button

    # Start the main event loop
    window.mainloop()


if __name__ == '__main__':
    selected_profile = search_linkedin()
    print("Your selected profile is: " + selected_profile)
    data = scrape_linkedin_profile(selected_profile)
    # Check if data was successfully scraped
    if data is not None:
        write_email(data)
    else:
        print("Exiting the program as no data was scraped.")

# Import necessary libraries
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import json
import requests
import openai
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Set up global variables
mongo_uri = "mongodb+srv://<user>:<password>@<cluster-url>/" # Use the actual URI
openai.api_key = os.environ.get('OPENAI_API_KEY') # Make sure this environment variable is set

# Function definitions

def search_linkedin():
    # Prompt the user for a search query
    query = input("Enter a name and organization (e.g., Bill Gates Microsoft): ")
    
    # Perform a Google search for the query with site:linkedin.com to limit to LinkedIn profiles
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}+site:linkedin.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    # Check if the request was successful
    if response.status_code != 200:
        print("Failed to retrieve search results.")
        return None

    # Parse the response using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract the URLs of the top LinkedIn results
    results = soup.find_all("div", class_="g")
    linkedin_urls = []
    for result in results[:5]:  # Limit to top 5 results
        link_element = result.find("a", href=True)
        if link_element and "linkedin.com/in" in link_element['href']:
            linkedin_urls.append(link_element['href'])

    # Prompt the user to select a LinkedIn result
    for i, url in enumerate(linkedin_urls):
        print(f"{i + 1}. {url}")
    selection = int(input("Select a LinkedIn profile by entering the number: ")) - 1

    # Check if the user made a valid selection
    if 0 <= selection < len(linkedin_urls):
        return linkedin_urls[selection]
    else:
        print("Invalid selection.")
        return None


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
    
    # Wait for the necessary elements to load on the page
    driver.implicitly_wait(5)  # This line may need adjustment based on page load times
    
    # Scroll to the bottom of the page to load all elements (if necessary)
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
        data = json.loads(script.string)
        
        # Extract the fields of interest from the JSON data
        # Note: This assumes the JSON-LD script tag contains the profile info in a structure under '@graph'
        person = [x for x in data['@graph'] if x.get('@type') == 'Person'][0]
        
        profile_data = {
            'name': person.get('name', ''),
            'job_title': person.get('jobTitle', ''),
            'company': person.get('worksFor', {}).get('name', ''),
            'location': person.get('address', {}).get('addressLocality', ''),
            'education': person.get('alumniOf', {}).get('name', ''),
            # Add more fields as necessary
        }
        
        # Connect to MongoDB and store the data
        client = MongoClient(mongo_uri)
        db = client.linkedin
        collection = db.profiles
        collection.insert_one(profile_data)
        
        print(f"Added {profile_data['name']} to MongoDB.")
        
        return profile_data
    else:
        print("Profile information could not be found.")
        return None

def write_email(profile_data):
    # Check if the OpenAI API key is set
    if not openai.api_key:
        raise ValueError("OpenAI API key is not set.")
    
    # Construct the prompt with the profile data
    prompt = (
        f"Write a professional email to {profile_data.get('name', 'there')} "
        f"inviting them to explore a potential collaboration opportunity. "
        f"Here's some information about them:\n"
        f"Name: {profile_data.get('name', 'N/A')}\n"
        f"Job Title: {profile_data.get('job_title', 'N/A')}\n"
        f"Company: {', '.join(profile_data.get('current_company_name', []))}\n"
        f"Location: {profile_data.get('location', 'N/A')}\n"
        f"Education: {profile_data.get('education', 'N/A')}\n"
        f"Previous Jobs: {profile_data.get('previous_jobs', 'N/A')}\n"
        f"About: {profile_data.get('about', 'N/A')}\n"
        f"The email should be polite, concise, and encourage a response. "
        f"End with a friendly sign-off and include a placeholder for our contact details."
    )
    
    try:
        # Make an API call to OpenAI to generate the email content
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=200,  # Adjust as necessary
            temperature=0.7  # A balance between creativity and coherence
        )
        
        # Extract the generated email from the response
        generated_email = response.choices[0].text.strip()
        
        # Print the generated email
        print("Generated email:")
        print(generated_email)
        
        # Return the generated email
        return generated_email
    
    except openai.error.OpenAIError as e:
        # Handle any errors that occur during the API call
        print(f"An error occurred while generating the email: {e}")
        return None

def write_email_gui(profile_data):
    # Function to generate the email using OpenAI API
    def generate_email():
        selected_info = {
            'name': name_var.get(),
            'job_title': job_title_var.get() and profile_data.get('job_title', ''),
            'company': company_var.get() and ', '.join(profile_data.get('current_company_name', [])),
            'education': education_var.get() and profile_data.get('education', ''),
            'about': about_var.get() and profile_data.get('about', '')
        }

        # Construct the prompt
        prompt = f"Write a professional email to {selected_info['name']} "
        prompt += "inviting them to a business opportunity at our company. "
        prompt += "The email should be friendly, engaging, and professional. Here is some information you can use:\n"
        prompt += "\n".join(f"{key.title()}: {value}" for key, value in selected_info.items() if value)
        prompt += "\nEnd the email with a friendly sign-off."
        
        try:
            # Make an API call to OpenAI to generate the email content
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=150,  # Adjust as needed
                temperature=0.7  # Adjust for creativity
            )
            
            # Display the generated email
            email_text.delete('1.0', tk.END)  # Clear existing text
            email_text.insert(tk.END, response.choices[0].text.strip())  # Insert new text
        
        except openai.error.OpenAIError as e:
            messagebox.showerror("Error", f"An error occurred while generating the email: {e}")

    # Create the main window
    window = tk.Tk()
    window.title("Email Generator")

    # Define variables for checkboxes
    name_var = tk.BooleanVar(value=True)
    job_title_var = tk.BooleanVar(value=True)
    company_var = tk.BooleanVar(value=True)
    education_var = tk.BooleanVar(value=True)
    about_var = tk.BooleanVar(value=True)

    # Add checkboxes to the GUI
    tk.Checkbutton(window, text="Include Name", var=name_var).pack(anchor='w')
    tk.Checkbutton(window, text="Include Job Title", var=job_title_var).pack(anchor='w')
    tk.Checkbutton(window, text="Include Company", var=company_var).pack(anchor='w')
    tk.Checkbutton(window, text="Include Education", var=education_var).pack(anchor='w')
    tk.Checkbutton(window, text="Include About", var=about_var).pack(anchor='w')

    # Add a text widget to display the generated email
    email_text = tk.Text(window, height=10, width=50)
    email_text.pack()

    # Add a button to generate the email
    generate_button = ttk.Button(window, text="Generate Email", command=generate_email)
    generate_button.pack(pady=10)

    # Start the GUI event loop
    window.mainloop()

# Main execution
if __name__ == '__main__':
    try:
        selected_profile_url = search_linkedin()
        if selected_profile_url:
            print(f"Your selected profile URL is: {selected_profile_url}")
            profile_data = scrape_linkedin_profile(selected_profile_url)
            if profile_data:
                # The GUI for writing email will be called here if profile scraping is successful
                write_email_gui(profile_data)
            else:
                print("Failed to scrape the LinkedIn profile. Exiting the program.")
        else:
            print("No LinkedIn profile selected. Exiting the program.")
    except Exception as e:
        print(f"An error occurred: {e}")
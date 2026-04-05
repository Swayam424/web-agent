from groq import Groq
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def search_web(driver, query):
    driver.get(f"https://duckduckgo.com/?q={query.replace(' ', '+')}")
    time.sleep(3)

def get_search_results(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []
    for a in soup.find_all("a", attrs={"data-testid": "result-title-a"})[:5]:
        href = a.get("href")
        title = a.get_text()
        if href and title:
            results.append({"title": title, "url": href})
    return results

def get_page_text(driver, url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:3000]

def think(task, context):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an autonomous web agent. Given a task and context from web pages, provide a comprehensive answer."},
            {"role": "user", "content": f"Task: {task}\n\nContext from web:\n{context}\n\nProvide your answer:"}
        ]
    )
    return response.choices[0].message.content

def run_agent(task):
    print(f"\nTask: {task}")
    print("Starting browser...")
    driver = create_browser()

    try:
        print("Searching DuckDuckGo...")
        search_web(driver, task)
        results = get_search_results(driver)

        if not results:
            print("No results found")
            return

        print(f"Found {len(results)} results. Reading articles...")
        all_content = ""
        for i, result in enumerate(results[:3]):
            print(f"Reading: {result['title']}")
            try:
                content = get_page_text(driver, result["url"])
                all_content += f"\n\nSource {i+1}: {result['title']}\n{content}"
            except:
                continue

        print("\nThinking...")
        answer = think(task, all_content)
        print(f"\nAnswer:\n{answer}")
        return answer

    finally:
        driver.quit()

if __name__ == "__main__":
    task = input("What should the agent do? > ")
    run_agent(task)
from mcp.server.fastmcp import FastMCP
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
mcp = FastMCP("web-agent", stateless_http=True, host="0.0.0.0")

def create_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless")
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

@mcp.tool()
async def search_and_answer(query: str) -> str:
    """Search the web and answer any question using real-time information."""
    driver = create_browser()
    try:
        search_web(driver, query)
        results = get_search_results(driver)
        if not results:
            return "No results found."
        all_content = ""
        for i, result in enumerate(results[:3]):
            try:
                content = get_page_text(driver, result["url"])
                all_content += f"\n\nSource {i+1}: {result['title']}\n{content}"
            except:
                continue
        return think(query, all_content)
    finally:
        driver.quit()

app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, forwarded_allow_ips="*", proxy_headers=True)
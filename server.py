from mcp.server.fastmcp import FastMCP
from groq import Groq
import httpx
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
mcp = FastMCP("web-agent", stateless_http=True, host="0.0.0.0")

async def search_web(query):
    url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client_http:
        r = await client_http.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for result in soup.find_all("div", class_="result")[:5]:
            title_tag = result.find("a", class_="result__a")
            snippet_tag = result.find("a", class_="result__snippet")
            if title_tag:
                results.append({
                    "title": title_tag.get_text(),
                    "snippet": snippet_tag.get_text() if snippet_tag else "",
                    "url": title_tag.get("href", "")
                })
        return results

async def fetch_page(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client_http:
        r = await client_http.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]

def think(task, context):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an autonomous web agent. Answer the task using the web context provided."},
            {"role": "user", "content": f"Task: {task}\n\nWeb context:\n{context}\n\nAnswer:"}
        ]
    )
    return response.choices[0].message.content

@mcp.tool()
async def search_and_answer(query: str) -> str:
    """Search the web and answer any question using real-time information."""
    results = await search_web(query)
    if not results:
        return "No results found."

    context = ""
    for i, r in enumerate(results[:3]):
        context += f"\nSource {i+1}: {r['title']}\n{r['snippet']}\n"
        try:
            page = await fetch_page(r['url'])
            context += page
        except:
            pass

    return think(query, context)

app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, forwarded_allow_ips="*", proxy_headers=True)
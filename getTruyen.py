import concurrent.futures

import requests
from bs4 import BeautifulSoup

# Create a session
session = requests.Session()


# Get list of chapter
def get_list_chapter(story_url):
    page = session.get(story_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    last_link = soup.select_one("#nav-intro > div > div.col-8 > table > tbody > tr:nth-child(3) > td:nth-child(2) > "
                                "ul > li > div.media-body > a").get("href")
    last_chapter = int(last_link[last_link.rfind("-") + 1:])
    base_url = story_url[:last_link.rfind("/")]
    return [base_url + "/chuong-" + str(i) for i in range(1, last_chapter + 1)]


# Get content of chapter
def get_content(chapter_url):
    page = session.get(chapter_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    div_tag = soup.select_one("#article")
    try:
        for tag in div_tag.find_all("div, script"):
            tag.extract()
    except AttributeError:
        print(f"\nError in {chapter_url}")
        return [None, None, None]

    h1_tag = soup.new_tag("h1")
    h1_tag.string = soup.select_one("#js-read__body > div.h1.mb-4.font-weight-normal.nh-read__title").string

    return [h1_tag, div_tag, int(chapter_url[chapter_url.rfind("-") + 1:])]


# Get story
def get_story(story_url):
    list_chapter = get_list_chapter(story_url)
    story = BeautifulSoup(
        "<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, "
        "initial-scale=1.0\"><link rel=\"stylesheet\" "
        "href=\"https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.5/css/bulma.min.css\"></head><body"
        "></body></html>", 'html.parser'
    )
    body = story.select_one("body")
    body.append(BeautifulSoup("<a name=\"start\"></a>", 'html.parser'))
    body.append(BeautifulSoup("<h1>Table of Contents</h1>", 'html.parser'))
    body.append(BeautifulSoup("<br>", 'html.parser'))

    div_tags_map = []
    for chapter in list_chapter:
        div_tag = story.new_tag("div", id=chapter[chapter.rfind("/") + 1:])
        div_tags_map.append(div_tag)

    count = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        chapter_futures = [executor.submit(get_content, chapter) for chapter in list_chapter]

        for future, chapter in zip(concurrent.futures.as_completed(chapter_futures), list_chapter):
            h1_tag, div_tag, index = future.result()
            if div_tag is not None:
                div_tags_map[index - 1].append(h1_tag)
                div_tags_map[index - 1].append(div_tag)
                count += 1
                print(f"\r({count}/{len(list_chapter)})  {h1_tag.string} done", end="")

    link_tags_map = []
    for chapter in div_tags_map:
        try:
            link_tag = story.new_tag("a", href=f"#{chapter['id']}")
            link_tag.string = chapter.select_one("h1").string
            link_tags_map.append(link_tag)
            link_tags_map.append(BeautifulSoup("<br>", 'html.parser'))
        except AttributeError:
            link_tags = story.new_tag("h2")
            link_tags.string = "Error in " + div_tags_map[div_tags_map.index(chapter) - 1].select_one("h1").string
            link_tags_map.append(link_tags)
            link_tags_map.append(BeautifulSoup("<br>", 'html.parser'))

    body.extend(link_tags_map)
    body.extend(div_tags_map)

    file_name = story_url[story_url.rfind("/") + 1:]
    with open(file_name + ".html", "w", encoding="utf-8") as file:
        file.write(str(story))
    print("\nDone")


if __name__ == '__main__':
    url = input("Enter url: ")
    get_story(url)

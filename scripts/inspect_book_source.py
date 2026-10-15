"""Read only the author's public book page and print its linked downloads."""
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request


class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, value in attrs:
                if key == "href":
                    print(value)


if __name__ == "__main__":
    raw = urllib.request.urlopen("https://udlbook.github.io/udlbook/", timeout=30).read()
    Path("docs/sources/udl_author_page.html").write_bytes(raw)
    Links().feed(raw.decode("utf-8"))
    scripts = re.findall(r'src="([^"]+\.js)"', raw.decode("utf-8"))
    for script in scripts[:1]:
        url = "https://udlbook.github.io" + script
        javascript = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
        Path("docs/sources/udl_author_bundle.js").write_text(javascript, encoding="utf-8")
        print("Official page bundle:", url)
        for match in re.findall(r'[^\s"\x27<>]{0,180}\.pdf', javascript):
            print(match)

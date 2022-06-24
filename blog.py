"""This is a sub 200 line (when not inculding comments)
   static site (blog) generator."""

import argparse
import datetime as dt
import json
import os
import shutil
from bs4 import BeautifulSoup
import markdown


def main():
    """The main blog handling script."""

    def log(log_message):
        """Handles writing log messages."""
        with open(os.path.join(PRI_LOG_DIR, "blog.log"), 'a', encoding='utf-8') as log_file:
            log_file.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S") + " - " + log_message + "\n")


    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r", encoding='utf-8') as jcf:
        j_conf = json.load(jcf)

    PUB_ROOT_DIR = j_conf['PUB_ROOT_DIR']
    PUB_POSTS_DIR = j_conf['PUB_POSTS_DIR']
    PUB_ASSETS_DIR = j_conf['PUB_ASSETS_DIR']
    PRI_LOG_DIR = j_conf['PRI_LOG_DIR']
    PRI_MARKDOWN_ARTICLES_DIR = j_conf['PRI_MARKDOWN_ARTICLES_DIR']

    # iterate over markdown article folders that have not been made public
    for ff_item in os.listdir(PRI_MARKDOWN_ARTICLES_DIR):
        if os.path.isdir(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item)) and ".PROCESSED." not in ff_item:
            update_flag = 0
            for filename in os.listdir(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item)):
                if filename.endswith(".md"):
                    # STEP 1: Convert markdown article to html, and then to beautiful soup object
                    with open(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item, filename), 'r', encoding='utf-8') as mdf:
                        text = mdf.read()
                        # https://python-markdown.github.io/extensions/
                        # https://github.com/Python-Markdown/markdown/issues/3
                        html = markdown.markdown(text, extensions=['fenced_code'])
                    html = '<div class="article">' + html + '</div>'
                    article_soup = BeautifulSoup(html, 'html.parser')

                    # STEP 2: Compute & create storage paths and names based on article title
                    # assumes first h3 tag is title name
                    article_title = str(article_soup.h3.text)
                    asset_dir_name = article_title.replace(" ", "-").lower()
                    article_filename = article_title.replace(" ", "-").lower() + ".html"
                    article_uri = article_filename

                    # duplicate article detection (implies update)
                    for asset_dir in os.listdir(PUB_ASSETS_DIR):
                        if str(asset_dir) == asset_dir_name:
                            update_flag = 1
                            log(f"Post {filename} --> {article_filename} was updated (one with the same name already existed and was overwritten).")

                    # this assumes you pushed assets (images, other files) up with your .md post
                    # ---------------------------------------------------------
                    # create folder for assets belonging to the currently processing post
                    # make sure this script is running with the right permissions to do so
                    article_asset_folder = os.path.join(PUB_ASSETS_DIR, asset_dir_name)
                    os.makedirs(article_asset_folder, exist_ok=True)
                    for fn in os.listdir(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item)):
                        if not fn.endswith('.md') and not os.path.isdir(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item, fn)):
                            shutil.copy2(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item, fn), os.path.join(article_asset_folder, fn))

                    # STEP 3: Modify all asset path names/destinations from local paths to server paths
                    for img in article_soup.find_all('img'):
                        # if asset is an external resource, leave as is, otherwise modify
                        if "https" not in img['src']:
                            # use elative reference (as to not reveal internal server paths)
                            img['src'] = os.path.join("..", "assets", asset_dir_name, img['src'])
                    for a_tag in article_soup.find_all('a'):
                        # if asset is an external resource, leave as is, otherwise modify
                        if "https" not in a_tag['href']:
                            # use elative reference (as to not reveal internal server paths)
                            a_tag['href'] = os.path.join("..", "assets", asset_dir_name, a_tag['href'])

                    # STEP 4: Use landing page, index.html, as a template and prepare to inject the article html into it to create an article
                    with open(os.path.join(PUB_ROOT_DIR, "index.html"), 'r', encoding='utf-8') as base_template:
                        base_template_soup = BeautifulSoup(base_template, 'html.parser')
                        base_template_soup.link['href'] = os.path.join("..", base_template_soup.link['href'])
                        base_template_soup.div.clear()
                        base_template_soup.div.append(article_soup)
                        base_template_soup.title.append(" - " + article_title)

                    # write new post to pub posts dir
                    with open(os.path.join(PUB_POSTS_DIR, article_filename), 'w', encoding='utf-8') as html_file:
                        html_file.write(str(base_template_soup))

                    log(f"Post {filename} --> {article_filename} went public in posts dir.")

                    # STEP 5: Build article preview and inject it into the homepage
                    # article_soup must be redeclared for some reason (disappears after being appended to another bs obj)
                    article_soup = BeautifulSoup(html, 'html.parser')
                    html_preview = BeautifulSoup('<div class="article-preview"></div>', 'html.parser')
                    # assumes title header
                    html_preview.div.append(article_soup.div.h3)
                    html_preview.div['id'] = asset_dir_name
                    # the next block uses the contents of the first four p tags to build the article preview
                    # the next four p tags should contain the following things in the listed order:
                    # author, date, img (all images are wrapped in p tags in the markdown spec), and introductory paragraph
                    # or -- author, date, and first two introductory paragraphs
                    for p_tag in article_soup.div.find_all("p", limit=4):
                        # if an image or other asset is present, modify resource location for correct relative location to index page
                        for img in p_tag.find_all('img'):
                            # if asset is an external resource, leave as is, otherwise modify
                            if "https" not in img['src']:
                                # use elative reference (as to not reveal internal server paths)
                                img['src'] = os.path.join("assets", asset_dir_name, img['src'])

                        for a_tag in p_tag.find_all('a'):
                            # if asset is an external resource, leave as is, otherwise modify
                            if "https" not in a_tag['href']:
                                # use elative reference (as to not reveal internal server paths)
                                a_tag['href'] = os.path.join("assets", asset_dir_name, a_tag['href'])

                        html_preview.div.append(p_tag)

                    # append article link to read full article
                    link = BeautifulSoup('<a href="">Read more</a>', 'html.parser')
                    link.a["href"] = os.path.join("posts", article_uri)
                    html_preview.div.append(link)

                    # open index/landing page to insert new post preview
                    with open(os.path.join(PUB_ROOT_DIR, "index.html"), 'r+', encoding='utf-8') as html_file:
                        base_template_soup = BeautifulSoup(html_file, 'html.parser')
                        if update_flag == 1:
                            soup = base_template_soup.div.find("div", id=asset_dir_name)
                            if soup:
                                soup.clear()
                                soup.append(html_preview)
                        else:
                            base_template_soup.div.insert(0, html_preview)
                        html_file.seek(0)
                        html_file.write(str(base_template_soup))
                        html_file.truncate()

                    log(f"Post {filename} --> {article_filename} went public on index page.")
            os.rename(os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ff_item), os.path.join(PRI_MARKDOWN_ARTICLES_DIR, ".PROCESSED." + ff_item))

# parse arguments
parser = argparse.ArgumentParser(description='A minimalist python blog.')
parser.add_argument('--setup', choices=["local", "server"], required=False, help='Initiates the blog setup process, creates required directories, installs required libraries.')
parser.add_argument('--remove-post', type=str, required=False, help='Removes a post given a title.')
args = parser.parse_args()

if args.setup == args.remove_post == None:
    if os.path.exists(os.path.join(os.path.dirname(__file__), "config.json")):
        main()
    else:
        print("[!] Please run setup first or help for detailed options.")
elif(args.setup and args.remove_post is None):
    d = {}
    if args.setup == "local":
        d['PUB_ROOT_DIR'] = os.getcwd()
        d['PRI_LOG_DIR'] = os.path.join(d['PUB_ROOT_DIR'], "logs")
        d['PRI_MARKDOWN_ARTICLES_DIR'] = os.path.join(d['PUB_ROOT_DIR'], "markdown-posts")
    elif args.setup == "server":
        d['PUB_ROOT_DIR'] = input("Please specify a web root directory for this project (for example, /var/www): ")
        PRI_DIR = os.getcwd()
        d['PRI_LOG_DIR'] = os.path.join(PRI_DIR, "logs")
        d['PRI_MARKDOWN_ARTICLES_DIR'] = os.path.join(PRI_DIR, "markdown-posts")

    d['PUB_POSTS_DIR'] = os.path.join(d['PUB_ROOT_DIR'], "posts")
    d['PUB_ASSETS_DIR'] = os.path.join(d['PUB_ROOT_DIR'], "assets")

    for dir_path in d.values():
        print(f"[*] Creating {dir_path} ...")
        os.makedirs(dir_path, exist_ok=True)

    os.rename(os.path.join(os.getcwd(), "index.html"), os.path.join(d['PUB_ROOT_DIR'], "index.html"))
    os.rename(os.path.join(os.getcwd(), "styles.css"), os.path.join(d['PUB_ASSETS_DIR'], "styles.css"))

    with open(os.path.join(os.path.dirname(__file__), "config.json"), "w", encoding="utf-8") as jcf:
        jcf.write(json.dumps(d))
    with open(os.path.join(d['PUB_ROOT_DIR'], "index.html"), 'r+', encoding='utf-8') as html_file:
        soup = BeautifulSoup(html_file, 'html.parser')
        blog_title = input("Enter your blog title: ")
        blog_tagline = input("Enter your blog tagline: ")
        soup.h1.string = blog_title
        p = soup.new_tag("p", attrs={'class': 'tagline'})
        p.string = blog_tagline
        soup.h1.append(p)
        soup.title = blog_title
        soup.link['href'] = os.path.join("assets", "styles.css")
        html_file.seek(0)
        html_file.write(str(soup))
        html_file.truncate()
elif(args.remove_post and args.setup is None):
    if os.path.exists(os.path.join(os.path.dirname(__file__), "config.json")):
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "r", encoding='utf-8') as jcf:
            j_conf = json.load(jcf)
        with open(os.path.join(j_conf['PUB_ROOT_DIR'], "index.html"), 'r+', encoding='utf-8') as html_file:
            soup = BeautifulSoup(html_file, 'html.parser')
            article_name = str(args.remove_post).replace(" ", "-").lower()
            ele = soup.div.find("div", id=article_name)
            if ele:
                ele.decompose()
                html_file.seek(0)
                html_file.write(str(soup))
                html_file.truncate()

                os.remove(os.path.join(j_conf['PUB_ROOT_DIR'], "posts", article_name.replace(" ", "-").lower() + ".html"))
                for file in os.listdir(os.path.join(j_conf['PUB_ROOT_DIR'], "assets", article_name.replace(" ", "-").lower())):
                    os.remove(os.path.join(j_conf['PUB_ROOT_DIR'], "assets", article_name.replace(" ", "-").lower(), file))
                os.rmdir(os.path.join(j_conf['PUB_ROOT_DIR'], "assets", article_name.replace(" ", "-").lower()))
            else:
                print("[!] No such article was found. Please check the article name and try again.")
else:
    print("[!] Only one action can be run at a time. Please see help for detailed options.")

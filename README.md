# KaramWS

**Karam Web Scraper.** Give it a link to an article, a section or a whole website, and it saves the articles as
Markdown files on your own computer. No account, no cloud.

- **An article** - saves that one article.
- **A section or category page** - walks its pages and saves every article.
- **A website's home page** - finds the articles through the sitemap (or the feeds) and saves them all.

The kind of link is detected automatically (you can also say it yourself). Pages that only show their content after
JavaScript runs are read with a real browser (Chromium, driven by Playwright), which the installers carry. It follows
`robots.txt`, pauses between requests, skips what it already saved, and can tell you with a desktop notification when
it is done.

## Use

Open **KaramWS** from your applications menu (or run `karamws-gui`), paste a link and press **Start**. The window asks
only for what changes from job to job: the link, what kind of link it is (usually detected for you) and the folder
(default `Documents/Articles`). **Stop** finishes the article being downloaded, then stops.

The first time it opens, a short **welcome guide** shows what it does, offers to download the browser (Chromium) when
the installation does not carry one, and lets you choose the folder.

From a terminal:

```bash
karamws "https://example.com/2026/some-post/"                 # one article
karamws "https://example.com/category/news/" -o articles      # a whole section
karamws "https://example.com/" --limit 20                     # the first 20 articles of a site
```

Options: `--kind {auto,article,section,site}`, `--limit N`, `--delay SECONDS`, `--ignore-robots`, `--no-browser`,
`--version`. The articles are saved as `output/<site>/<title>-<hash>.md`; running again skips what is already saved,
so an interrupted run can simply be started again.

## License

AGPL-3.0-or-later. See `LICENSE`. Copyright 2026 AbuKaram01.

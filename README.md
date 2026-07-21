# #KostasThoughts

A local-only static archive generated from:

`kostas thoughts.txt`

The page runs entirely offline using `index.html`, `style.css`, `script.js`, and `posts.json`.

## Extraction

The source text file was treated as read-only and was not modified.

The file contains one X status URL per post, separated by blank lines. The generator splits the file on blank-line-separated blocks, removes duplicate status IDs, and preserves each original block exactly as the post `text`.

Because the source file contains URLs only, tweet body text is cached separately in `tweet_cache.json` using public X/Twitter oEmbed metadata. Dates are inferred offline from X/Twitter snowflake status IDs. Topics and question-style link titles are inferred from cached tweet text when available.

Generated review result:

- `posts_review.json`
- Detected unique posts: 127
- Cached tweet texts: 126
- Manual tweet text overrides: 3
- URL-only fallbacks: 0

## Regenerate `posts.json`

From this folder:

```bash
python3 fetch_tweets.py
```

```bash
python3 generate_posts.py
```

If the source text file is stored elsewhere, pass it explicitly:

```bash
python3 fetch_tweets.py --input "/path/to/kostas thoughts.txt"
python3 generate_posts.py --input "/path/to/kostas thoughts.txt"
```

To regenerate the review file first:

```bash
python3 generate_posts.py --review
```

## Run Locally

From this folder:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

No network access, uploads, publishing, git repository creation, or commits are required.

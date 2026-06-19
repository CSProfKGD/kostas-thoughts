#!/usr/bin/env python3
"""Generate local post data from the read-only Kosta's Thoughts text export."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INPUT_FILE = Path("kostas thoughts.txt")
CACHE_FILE = Path("tweet_cache.json")
TWITTER_EPOCH_MS = 1288834974657
STATUS_RE = re.compile(r"https?://(?:x|twitter)\.com/[^/\s]+/status/(\d+)(?:\?[^\s]*)?", re.I)
URL_RE = re.compile(r"https?://\S+")
HASHTAG_RE = re.compile(r"#\w+")
MENTION_RE = re.compile(r"@\w+")
ADDITIONAL_TWEET_URLS = [
    "https://x.com/CSProfKGD/status/2067935592361369920?s=20",
]
QUESTION_OVERRIDES = {
    "2067935592361369920": "What does academic research look like in 2026?",
    "2037416736904052837": "How should images and videos bleed beyond slide boundaries?",
    "2037409261429653829": "Curious about the \"Keynote magic\" behind my slides?",
    "2035331378582093998": "How will LLM agents change the way newcomers learn research?",
    "2035064787164402099": "What happens when casual lab style suddenly changes?",
    "1922401234348073114": "How should related work contextualize a paper's contribution?",
    "1920180821413003506": "How should researchers handle another round of conference reviews?",
    "1900998474268643662": "How will AI assistants change assignment design?",
    "1898016162987806921": "How should authors communicate with conference organizers?",
    "1886178291351994434": "How should area chairs read rebuttals beyond one review?",
    "1883904287459467715": "Why should presentations be mapped out before making slides?",
    "1882841750009762230": "Why is persistence essential in academia?",
    "1882091136439001227": "How can academics guard their free time?",
    "1879530836787429622": "When does a missing review become irresponsible?",
    "1866880672704729169": "Why should figures use vector images?",
    "1863923722014339123": "How can computer science better showcase itself?",
    "1863558702353002800": "Why should presenters stop using bullet-heavy slides?",
    "1855663203163734202": "Why should figure captions walk readers through the figure?",
    "1854218703967334862": "Why do early researchers need a web and social media presence?",
    "1839690270234890626": "How can broad researchers make their work easier to recognize?",
    "1835427195566670245": "How readable should figure text be in a paper?",
    "1773724533444280355": "Why should plots avoid rasterized image formats?",
    "1754260946179002523": "Why must researchers learn to push through failure?",
    "1753894844957622307": "How should reviewers respond when a rebuttal changes their mind?",
    "1751684843677610068": "How should authors respond when conference issues arise?",
    "1751663818235682951": "What submission problems can lead to desk rejection?",
    "1744721617232830942": "Why should late reviewers keep area chairs informed?",
    "1743043604153790517": "How can smaller conferences help build long-term connections?",
    "1729159371861717424": "What makes an undergraduate education prepare you for lifelong learning?",
    "1717039520229544268": "What is the foundation of healthy student supervision?",
    "1685622625211486208": "Why should researchers seek strong senior mentors?",
    "1685322806819426304": "How can retweets and likes help early researchers?",
    "1685288386775359489": "Why should younger researchers take real breaks?",
    "1680615121066786816": "Why should more people serve as program chairs?",
    "1662460775242375169": "When should authors message an area chair privately?",
    "1637836860171886594": "Why should faculty be good colleagues inside the department?",
    "1637574035449040896": "How could conference governance broaden participation?",
    "1625864981831905284": "How should junior researchers use social media to share their work?",
    "1625856302852476934": "How can nervous presenters grow into confident speakers?",
    "1621139115222892552": "How should reviewers approach the discussion period?",
    "1618955219383238656": "How can likes and retweets build an early research network?",
    "1603757483771809792": "Why is writing part of the research process?",
    "1599767000770699264": "Why are unsolicited email reminders rarely gentle?",
    "1593673404909068289": "Why is performance not itself a paper contribution?",
    "1592164963795501056": "Why should video papers include supplemental videos?",
    "1588650313363648512": "Why should unusually good results trigger skepticism?",
    "1584580437774454784": "How can conferences expand your research network?",
    "1563140240646479873": "Why are supplemental videos useful for video papers?",
    "1555547392052789251": "How can academics amplify students' work online?",
    "1517305180219392000": "What should online teaching teach us for future courses?",
    "1501209804945166338": "Why do slide fonts tend to get larger with experience?",
    "1497987085344587778": "Why should writing not wait until the deadline?",
    "1497955678094340106": "How can researchers pay mentorship forward?",
    "1487095932764270596": "Should extra reviews come with extra rebuttal space?",
    "1486790120711893002": "How should reviewers put ego aside after a rebuttal?",
    "1484251167383330819": "Why does a great lecture feel like a great swing?",
    "1481480062096523266": "Why do late submissions cost area chairs valuable time?",
    "1471158646847516674": "How can academic Twitter enrich teaching?",
}
TOPIC_OVERRIDES = {
    "2067935592361369920": "AI & Tools",
    "2037416736904052837": "Teaching & Presentations",
    "2037409261429653829": "Teaching & Presentations",
    "2029603806753743093": "Research Practice",
    "2021963774715109769": "Research Practice",
    "2020573376486527022": "Research Practice",
    "1866880672704729169": "Research Practice",
    "1863280731721486441": "Mentoring & Students",
    "1855663203163734202": "Research Practice",
    "1751684843677610068": "Peer Review & Conferences",
    "1743043604153790517": "Peer Review & Conferences",
    "1685288386775359489": "Personal Reflections",
    "1599767000770699264": "Productivity",
    "1521178905494933504": "Teaching & Presentations",
    "1514229780488540162": "Research Practice",
    "1488905123153821702": "Productivity",
}
MANUAL_TWEET_TEXT = {
    "2037416736904052837": "#KostasThoughts: Using images/videos in your slides?\n\nDesign your slide so that the imagery bleeds over the image boundaries.",
    "2037409261429653829": "#KostasKeynoteLessons: Still curious about the \"Keynote magic\" behind my slides?\n\nCheck out the full Keynote source files for my lectures on\n\nFlow Matching\nGaussian Splatting\nTransformers\n\nGrab the files in the thread and feel free to remix.",
}


def date_from_status_id(status_id: str) -> str:
    timestamp_ms = (int(status_id) >> 22) + TWITTER_EPOCH_MS
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()


def clean_tweet_text(text: str) -> str:
    text = text.replace("#KostasThoughts :", "").replace("#KostasThoughts", "")
    text = text.replace("#KostasKeynoteLessons :", "").replace("#KostasKeynoteLessons", "")
    text = URL_RE.sub("", text)
    text = re.sub(r"pic\.twitter\.com/\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" :-")


def title_case_phrase(text: str, max_words: int = 11) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text)
    phrase = " ".join(words[:max_words])
    phrase = MENTION_RE.sub("", phrase).strip()
    return phrase[:1].lower() + phrase[1:] if phrase else "this thought"


def summary_question(text: str, status_id: str, date: str | None) -> str:
    if status_id in QUESTION_OVERRIDES:
        return QUESTION_OVERRIDES[status_id]

    cleaned = clean_tweet_text(text)
    lowered = cleaned.lower()

    patterns = [
        (["visual analogies", "section title"], "How can visual analogies make lecture sections easier to follow?"),
        (["recording lectures", "share them publicly"], "How can recorded lectures become useful public teaching resources?"),
        (["automating slide creation", "learning process"], "Why can making slides be part of learning the material?"),
        (["eyeballs are mine", "one idea at a time"], "How should each slide focus the audience on one idea at a time?"),
        (["endless reading", "procrastination"], "When does reading papers become procrastination?"),
        (["award-winning papers"], "What should award-winning papers demonstrate?"),
        (["code/weights", "desk reject"], "Should promised code and weights be available by conference time?"),
        (["get it in writing"], "Why should junior faculty get important promises in writing?"),
        (["reviewers", "reasoning", "area chair"], "What should area chairs look for in reviewer reasoning?"),
        (["reviewer pool", "per paper nomination"], "Should conferences rethink who enters the reviewer pool?"),
        (["small gestures"], "Why do small gestures after meetings matter?"),
        (["one life", "long game"], "How can loss clarify the importance of playing the long game?"),
        (["multimedia-style articles", "distill"], "Should conferences create tracks for multimedia research articles?"),
        (["static pdf", "static papers"], "How should research papers move beyond static PDFs?"),
        (["family, friends and loved ones"], "How can we be more present with loved ones?"),
        (["students", "reviews", "critical"], "How can students learn to write more constructive reviews?"),
        (["desk reject", "conference"], "When should conference policy lead to desk rejection?"),
        (["talk", "presentation", "slides"], "How can presentations better serve the audience?"),
        (["slide", "audience"], "How can slide design guide audience attention?"),
        (["lecture", "teaching"], "How can teaching materials become clearer over time?"),
        (["faculty", "academia"], "What should faculty keep in mind about academic life?"),
        (["paper", "review"], "How can peer review become more useful and fair?"),
        (["research", "paper"], "How can researchers improve the way they communicate work?"),
        (["phd", "student"], "What should PhD students remember during the research journey?"),
        (["deadline", "conference"], "How should researchers handle conference deadline pressure?"),
        (["ai", "genai"], "How is AI changing academic and presentation workflows?"),
        (["vo₂ max", "consistent"], "What does steady fitness progress look like over time?"),
        (["venue macros", "bibtex"], "Why are venue macros useful in BibTeX?"),
        (["ends don’t justify the means"], "Why do research methods matter as much as results?"),
        (["intermediate", "raw project results"], "Why should researchers keep intermediate project results?"),
        (["don’t reuse other people’s slides"], "Why is rebuilding slides part of understanding a topic?"),
        (["don’t plan talks by slide count"], "How should talks be planned by pace instead of slide count?"),
        (["don’t make my mistakes"], "How can students learn from their mentor’s mistakes?"),
        (["one idea per slide"], "Why should slides carry one idea at a time?"),
        (["review process has been disappointing"], "What makes a review process disappointing?"),
        (["admissions portal"], "Why is a professor’s email not an admissions portal?"),
        (["ai tools to write reviews"], "Why should reviewers write authentic reviews themselves?"),
        (["resilience gets you past the nos"], "How does resilience help in academia?"),
        (["related work", "laundry list"], "How should related work explain relationships between papers?"),
        (["rebuttals", "reviewer psychology"], "How should authors think about rebuttals?"),
        (["missing citations"], "When are missing citations truly critical in a review?"),
        (["letterwriters", "sufficient notice"], "How much notice should letter writers receive?"),
        (["colour choices in plots"], "How can plots be made more accessible?"),
        (["cups with lids"], "Why might cups with lids save your desk setup?"),
        (["core math", "computervision"], "What math background helps students study computer vision?"),
        (["svd", "linear algebra"], "Why should SVD be standard in linear algebra for computer science?"),
        (["first few years of teaching"], "Why do the first years of teaching feel so hard?"),
        (["faculty position", "photo", "marital status"], "What should faculty applicants leave out of a CV?"),
        (["leaving academia for industry"], "How should academics recalibrate around industry moves?"),
        (["online conferences", "ignore me for the day"], "What makes online conferences hard to separate from home life?"),
        (["promising, borderline", "next conference"], "Why can punting borderline papers harm promising work?"),
        (["contextualize your recommendations"], "Why should reviewers contextualize their recommendations?"),
        (["storyboarding", "flow matching"], "How can storyboarding help design a new lecture?"),
        (["backprop", "modular approach"], "Why can a modular view make backprop easier to understand?"),
        (["semi-transparent overlay", "code"], "How can overlays focus attention on code during a lecture?"),
        (["apple’s keynotes", "prezi ideas"], "What can presenters learn from Apple keynotes?"),
        (["perceptual organization"], "How can perceptual organization improve presentations?"),
        (["presentationzen", "visuals"], "How can visuals transform a standard slide?"),
        (["dual display", "eye contact"], "How can room setup help a lecturer maintain eye contact?"),
        (["spin wheel", "keynote"], "When is it time to replace a presentation laptop?"),
        (["presentation zen", "must read"], "What book can help improve presentations?"),
        (["presentation feedback", "students"], "Why are students often the toughest presentation critics?"),
        (["stress levels", "dissertation defence"], "What does dissertation defense stress look like?"),
        (["animations should guide attention"], "When do animations help rather than distract?"),
        (["magic", "prezis"], "How can Keynote tricks make presentations feel more polished?"),
        (["life", "family"], "What matters when life puts work in perspective?"),
    ]
    for keywords, question in patterns:
        if all(keyword in lowered for keyword in keywords):
            return question

    if "?" in cleaned:
        first_question = cleaned.split("?")[0].strip()
        if 8 <= len(first_question) <= 110:
            return f"{first_question}?"

    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    first_lower = first_sentence.lower()
    if first_lower.startswith("please "):
        phrase = first_sentence[7:].strip(" .")
        return f"Why should we {phrase}?"
    if first_lower.startswith("don’t ") or first_lower.startswith("don't "):
        phrase = re.sub(r"^don[’']t\s+", "", first_sentence, flags=re.I).strip(" .")
        return f"Why shouldn't we {phrase}?"
    if first_lower.startswith("do not "):
        phrase = first_sentence[7:].strip(" .")
        return f"Why shouldn't we {phrase}?"

    phrase = title_case_phrase(first_sentence)
    if phrase != "this thought":
        return f"What is the main lesson about {phrase}?"
    if date:
        return f"What was the thought from {date}?"
    return f"What is the key idea in thought {status_id}?"


def infer_topic(text: str) -> tuple[str, str | None]:
    lowered = text.lower()
    keyword_topics = [
        ("Teaching & Presentations", ["slide", "slides", "lecture", "teaching", "audience", "prezi", "presentation", "keynote", "storyboard", "visual", "projector"]),
        ("Peer Review & Conferences", ["review", "reviewer", "reviewers", "area chair", "conference", "desk reject", "deadline", "rebuttal", "cvpr", "iccv", "eccv", "neurips"]),
        ("Research Practice", ["research", "paper", "papers", "experiments", "reproducibility", "code/weights", "literature", "distill", "static pdf"]),
        ("Academia & Faculty Life", ["academia", "academic", "faculty", "tenure", "university", "professor", "administrator"]),
        ("Mentoring & Students", ["mentor", "mentoring", "student", "students", "advisor", "advisee", "phd", "dissertation", "defence"]),
        ("AI & Tools", ["ai", "genai", "llm", "machine learning", "computer vision", "model", "ideogram", "generative"]),
        ("Career", ["career", "job", "interview", "promotion", "hiring", "industry", "cv"]),
        ("Productivity", ["productivity", "writing", "focus", "habit", "procrastination", "time", "workflow"]),
        ("Personal Reflections", ["life", "family", "friends", "loved ones", "parent", "dad", "present", "small gestures", "long game"]),
        ("Humour", ["humor", "humour", "funny", "joke", "😅", "🤓", "😉", "😬"]),
    ]
    scores: dict[str, int] = {}
    for topic, keywords in keyword_topics:
        score = 0
        for keyword in keywords:
            if len(keyword) <= 3 and keyword.isascii() and keyword.isalpha():
                if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", lowered):
                    score += 1
            elif keyword in lowered:
                score += 1
        if score:
            scores[topic] = score
    if scores:
        return max(keyword_topics, key=lambda item: (scores.get(item[0], 0), -keyword_topics.index(item)))[0], None
    return "Miscellaneous", "URL archive"


def load_cache() -> dict[str, dict[str, str | None]]:
    if not CACHE_FILE.exists():
        return {}
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return cache.get("tweets", {})


def parse_posts(input_file: Path) -> list[dict[str, str | None]]:
    raw = input_file.read_text(encoding="utf-8")
    cache = load_cache()
    entries = [block.strip() for block in re.split(r"\n\s*\n", raw) if block.strip()]
    entries.extend(ADDITIONAL_TWEET_URLS)
    posts = []
    seen: set[str] = set()

    for entry in entries:
        match = STATUS_RE.search(entry)
        status_id = match.group(1) if match else None
        dedupe_key = status_id or entry
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        date = date_from_status_id(status_id) if status_id else None
        cached = cache.get(status_id or "", {})
        fetched_text = MANUAL_TWEET_TEXT.get(status_id or "") or cached.get("text") or ""
        source_text = fetched_text or entry
        topic, subtopic = infer_topic(source_text)
        if status_id in TOPIC_OVERRIDES:
            topic = TOPIC_OVERRIDES[status_id]
            subtopic = None
        posts.append(
            {
                "id": status_id or f"post-{len(posts) + 1:03d}",
                "date": date,
                "text": source_text,
                "url": match.group(0) if match else None,
                "title": summary_question(source_text, status_id or str(len(posts) + 1), date),
                "summary_question": summary_question(source_text, status_id or str(len(posts) + 1), date),
                "topic": topic,
                "subtopic": subtopic,
            }
        )

    return posts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local JSON post data.")
    parser.add_argument("--review", action="store_true", help="write posts_review.json instead of posts.json")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE, help="path to the source text file")
    args = parser.parse_args()

    posts = parse_posts(args.input)
    output = {
        "source": args.input.name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "post_count": len(posts),
        "notes": [
            "Input was treated as read-only.",
            "Posts were split on blank-line-separated blocks.",
            "The source file contains URL entries only; tweet text was added from local tweet_cache.json when available.",
            "Dates were inferred offline from X/Twitter snowflake status IDs where available.",
            "Topics and summary questions were inferred locally from cached tweet text.",
        ],
        "posts": posts,
    }

    target = Path("posts_review.json" if args.review else "posts.json")
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {target} with {len(posts)} posts.")


if __name__ == "__main__":
    main()

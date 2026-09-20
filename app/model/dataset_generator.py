"""
dataset_generator.py
---------------------
Generates a labeled training set of URLs (legit=0 / phishing=1) using
randomized but realistic patterns, so the whole project can be trained
and demoed with zero external dependencies or API keys.

For a real-world / resume-grade version, swap this out for:
  - PhishTank verified feed:      https://phishtank.org/developer_info.php
  - UCI Phishing Websites Dataset: https://archive.ics.uci.edu/dataset/327
  - OpenPhish feed:                https://openphish.com/

Just replace generate_dataset() with a CSV loader that yields
(url, label) pairs and the rest of the pipeline (feature_extractor,
train_model) works unchanged.
"""

import random
import csv
import os

random.seed(42)

LEGIT_DOMAINS = [
    "github.com", "google.com", "wikipedia.org", "amazon.com", "microsoft.com",
    "stackoverflow.com", "linkedin.com", "reddit.com", "nytimes.com", "bbc.com",
    "spotify.com", "netflix.com", "apple.com", "dropbox.com", "salesforce.com",
    "notion.so", "figma.com", "coursera.org", "khanacademy.org", "python.org",
]

LEGIT_PATHS = [
    "/", "/about", "/products", "/docs/getting-started", "/blog/2026/07/update",
    "/user/settings", "/search?q=python", "/pricing", "/contact", "/help/faq",
]

PHISHING_BRANDS = [
    "paypal", "amazon", "apple", "microsoft", "netflix", "bankofamerica",
    "chase", "wellsfargo", "google", "facebook", "instagram", "irs",
]

PHISHING_TEMPLATES = [
    "http://{brand}-secure-login.{tld}/verify",
    "http://{brand}.{rand}.{tld}/account/update",
    "http://secure-{brand}-{rand}.com/signin?token={num}",
    "http://{ip}/verify/{brand}/login.php",
    "http://{brand}-support-{rand}.{tld}/webscr?cmd=login",
    "http://{rand}.{tld}/{brand}/confirm-password",
    "https://{brand}.account-verify-{rand}.{tld}/",
    "http://{brand}login.{tld}-secure.{tld2}/index.html",
]

SUSPICIOUS_TLDS = ["tk", "ml", "ga", "cf", "gq", "xyz", "top", "info"]


def _rand_str(n=6):
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))


def _rand_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def _make_legit_url():
    domain = random.choice(LEGIT_DOMAINS)
    path = random.choice(LEGIT_PATHS)
    scheme = "https"
    sub = random.choice(["", "www.", "app.", "docs."])
    return f"{scheme}://{sub}{domain}{path}"


def _make_phishing_url():
    template = random.choice(PHISHING_TEMPLATES)
    return template.format(
        brand=random.choice(PHISHING_BRANDS),
        tld=random.choice(SUSPICIOUS_TLDS),
        tld2=random.choice(["com", "net"]),
        rand=_rand_str(random.randint(4, 8)),
        num=random.randint(1000, 999999),
        ip=_rand_ip(),
    )


def generate_dataset(n_per_class=1500):
    rows = []
    for _ in range(n_per_class):
        rows.append((_make_legit_url(), 0))
    for _ in range(n_per_class):
        rows.append((_make_phishing_url(), 1))
    random.shuffle(rows)
    return rows


def save_dataset(path="data/urls_dataset.csv", n_per_class=1500):
    rows = generate_dataset(n_per_class)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "label"])
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    save_dataset()

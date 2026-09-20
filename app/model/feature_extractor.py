"""
feature_extractor.py
---------------------
Turns a raw URL into a fixed-length numeric feature vector that the
ML model can score. No external network calls are required, so this
runs identically during training and during live browser-extension
requests (fast, offline-safe, no rate limits).

Feature families:
  1. Lexical / structural  (length, dots, hyphens, @ signs, digits ...)
  2. Suspicious tokens      (login, verify, secure, bank, update ...)
  3. Domain-level signals   (IP-as-host, punycode, many subdomains ...)
  4. Security signals       (https usage, port in URL, shortener use)
"""

import re
import math
from urllib.parse import urlparse

SUSPICIOUS_WORDS = [
    "login", "verify", "update", "secure", "account", "bank", "confirm",
    "signin", "password", "webscr", "billing", "suspend", "urgent",
    "click", "limited", "unlock", "security", "alert", "recover",
]

SHORTENER_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "adf.ly", "shorte.st", "rebrand.ly",
]

FEATURE_NAMES = [
    "url_length", "hostname_length", "path_length", "num_dots",
    "num_hyphens", "num_underscores", "num_slashes", "num_digits",
    "num_at_signs", "num_question_marks", "num_equal_signs",
    "num_percent", "num_ampersands", "has_ip_host", "has_port",
    "is_https", "num_subdomains", "suspicious_word_count",
    "has_shortener", "digit_letter_ratio", "hostname_entropy",
    "has_https_in_path_not_host", "count_www", "has_hyphen_in_domain",
]

IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    probs = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in probs)


def extract_features(url: str) -> dict:
    """Return an ordered dict of numeric features for a single URL."""
    url = url.strip()
    if not re.match(r"^[a-zA-Z]+://", url):
        # assume http(s) missing scheme, so urlparse doesn't misparse
        parsed_guess = "http://" + url
    else:
        parsed_guess = url

    parsed = urlparse(parsed_guess)
    hostname = parsed.hostname or ""
    path = parsed.path or ""

    feats = {}
    feats["url_length"] = len(url)
    feats["hostname_length"] = len(hostname)
    feats["path_length"] = len(path)
    feats["num_dots"] = url.count(".")
    feats["num_hyphens"] = url.count("-")
    feats["num_underscores"] = url.count("_")
    feats["num_slashes"] = url.count("/")
    feats["num_digits"] = sum(c.isdigit() for c in url)
    feats["num_at_signs"] = url.count("@")
    feats["num_question_marks"] = url.count("?")
    feats["num_equal_signs"] = url.count("=")
    feats["num_percent"] = url.count("%")
    feats["num_ampersands"] = url.count("&")
    feats["has_ip_host"] = 1 if IP_REGEX.match(hostname) else 0
    feats["has_port"] = 1 if (parsed.port is not None) else 0
    feats["is_https"] = 1 if parsed.scheme == "https" else 0
    feats["num_subdomains"] = max(hostname.count(".") - 1, 0)
    feats["suspicious_word_count"] = sum(
        1 for w in SUSPICIOUS_WORDS if w in url.lower()
    )
    feats["has_shortener"] = 1 if any(
        s in hostname for s in SHORTENER_DOMAINS
    ) else 0
    letters = sum(c.isalpha() for c in url)
    feats["digit_letter_ratio"] = (
        feats["num_digits"] / letters if letters > 0 else 0.0
    )
    feats["hostname_entropy"] = _shannon_entropy(hostname)
    feats["has_https_in_path_not_host"] = 1 if (
        "https" in (path + (parsed.query or "")).lower()
    ) else 0
    feats["count_www"] = url.lower().count("www")
    feats["has_hyphen_in_domain"] = 1 if "-" in hostname else 0

    return feats


def features_to_vector(feats: dict):
    """Convert the dict from extract_features() into an ordered list
    matching FEATURE_NAMES, for feeding into sklearn."""
    return [feats[name] for name in FEATURE_NAMES]


if __name__ == "__main__":
    sample = "http://secure-login-update.bank-of-verify.com/account@id?token=123"
    print(extract_features(sample))

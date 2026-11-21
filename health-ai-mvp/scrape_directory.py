import json
import time
from urllib.parse import urljoin
import re 

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.medicosdeelsalvador.com/"

# Start from doctor-heavy specialty pages
START_PATHS = [
    "/especialidades-de-medicina/cardiologos",
    "/especialidades-de-medicina/dermatologos",
    "/especialidades-de-medicina/gastroenterologos",
    "/especialidades-de-medicina/neumologos",
    "/especialidades-de-medicina/medicina-interna",
    "/medicos-cirujanos/otorrinolaringologos",
    "/medicos-cirujanos/neurocirujanos",
    "/pediatras/cardiologos",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch(url: str) -> str | None:
    try:
        with httpx.Client(
            headers=HEADERS,
            timeout=30.0,
            follow_redirects=True,
            http2=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"Failed fetch {url}: {e}")
        return None


def looks_like_doctor_profile(url: str, anchor_text: str) -> bool:
    u = url.lower()
    t = anchor_text.lower().strip()

    # Strong signals
    if "/doctor/" in u or "/medico/" in u:
        return True

    # Most actual doctor profiles on this site end with _###.html and often include dr/dra in url or text
    if u.endswith(".html") and (
        "/especialidades-de-medicina/" in u or
        "/medicos-cirujanos/" in u or
        "/pediatras/" in u
    ):
        if "dr-" in u or "dra-" in u or t.startswith("dr.") or t.startswith("dra."):
            return True

    return False


def extract_profile_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)

        if not href:
            continue

        absolute = urljoin(base_url, href)

        if "www.medicosdeelsalvador.com" not in absolute:
            continue

        if looks_like_doctor_profile(absolute, text):
            links.add(absolute)

    return sorted(links)


def extract_next_page_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True).lower()

        if not href:
            continue

        absolute = urljoin(base_url, href)

        if "www.medicosdeelsalvador.com" not in absolute:
            continue

        if text in {"siguiente", "2", "3", "4", "5", "6", "7", "8"}:
            links.add(absolute)

    return sorted(links)


def extract_title_name(soup: BeautifulSoup, url: str) -> str:
    # Prefer h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)

    # Fallback to title
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        # Remove site suffix if present
        title = title.split(" en Médicos de El Salvador")[0].strip()
        return title

    return url


def should_keep_profile(name: str, url: str, text: str) -> bool:
    name_l = name.lower()
    url_l = url.lower()
    text_l = text.lower()

    blocked_name_terms = [
        "asociación",
        "clinica",
        "clínica",
        "cardiolab",
        "centro",
        "hospital",
        "laboratorio",
        "óptica",
        "farmacia",
    ]

    if any(term in name_l for term in blocked_name_terms):
        return False

    if "/clinicas/" in url_l or "/asociaciones-de-pacientes/" in url_l:
        return False

    if name_l.startswith("dr.") or name_l.startswith("dra."):
        return True

    if " dr. " in f" {text_l} " or " dra. " in f" {text_l} ":
        return True

    return False


def parse_profile_page(url: str, html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text(" ", strip=True)

    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)
    elif soup.title:
        name = soup.title.get_text(" ", strip=True).split(" en Médicos de El Salvador")[0].strip()
    else:
        return None

    name_lower = name.lower()
    if not (name_lower.startswith("dr.") or name_lower.startswith("dra.")):
        return None

    image_url = ""

    # Try first meaningful image from the page
    for img in soup.find_all("img", src=True):
        src = img["src"].strip()
        alt = (img.get("alt") or "").lower()
        cls = " ".join(img.get("class", []))
        absolute = urljoin(url, src)

        if not src:
            continue

        # Skip logos/icons/placeholders as best effort
        bad_words = ["logo", "banner", "icon", "loading", "placeholder"]
        if any(word in absolute.lower() for word in bad_words):
            continue

        # Prefer images likely tied to doctor/profile/gallery
        if name.split()[0].lower() in alt or "doctor" in alt or "perfil" in alt or "profile" in cls.lower():
            image_url = absolute
            break

        # If nothing better, keep first viable image
        if not image_url:
            image_url = absolute

    return {
        "name": name,
        "profile_url": url,
        "image_url": image_url,
        "raw_text": page_text
    }


def collect_listing_and_pagination(start_url: str) -> tuple[list[str], list[str]]:
    visited_listing_pages = set()
    to_visit = [start_url]
    all_profile_links = set()

    while to_visit:
        current = to_visit.pop(0)
        if current in visited_listing_pages:
            continue

        visited_listing_pages.add(current)
        print(f"Listing page: {current}")

        html = fetch(current)
        if not html:
            continue

        profile_links = extract_profile_links(html, BASE_URL)
        for link in profile_links:
            all_profile_links.add(link)

        next_pages = extract_next_page_links(html, BASE_URL)
        for next_page in next_pages:
            if next_page not in visited_listing_pages and next_page not in to_visit:
                to_visit.append(next_page)

        time.sleep(0.5)

    return sorted(visited_listing_pages), sorted(all_profile_links)

def is_likely_bad_image(url: str, alt_text: str = "", class_text: str = "") -> bool:
    haystack = f"{url} {alt_text} {class_text}".lower()

    blocked_terms = [
        "logo",
        "icon",
        "banner",
        "placeholder",
        "loading",
        "facebook",
        "instagram",
        "twitter",
        "youtube",
        "whatsapp",
        "ads",
        "advert",
        "favicon",
        "spinner",
        "pixel",
    ]

    return any(term in haystack for term in blocked_terms)


def score_image_candidate(img, absolute_url: str, doctor_name: str) -> int:
    score = 0

    alt_text = (img.get("alt") or "").strip().lower()
    class_text = " ".join(img.get("class", [])).lower()
    width = str(img.get("width", "")).strip()
    height = str(img.get("height", "")).strip()

    if is_likely_bad_image(absolute_url, alt_text, class_text):
        return -100

    # Strong signals
    if "doctor" in alt_text or "doctora" in alt_text or "doctor" in class_text or "perfil" in class_text:
        score += 20

    # If doctor name appears in alt text, that's excellent
    doctor_name_parts = [p.lower() for p in doctor_name.split() if len(p) > 2]
    if doctor_name_parts and any(part in alt_text for part in doctor_name_parts):
        score += 25

    # Profile-ish filenames/classes
    if any(word in absolute_url.lower() for word in ["doctor", "doctora", "perfil", "medico"]):
        score += 10

    # Prefer jpg/jpeg/png/webp
    if re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", absolute_url.lower()):
        score += 8

    # Prefer decent visible size
    try:
        if width and int(width) >= 120:
            score += 5
        if height and int(height) >= 120:
            score += 5
    except ValueError:
        pass

    return score


def extract_doctor_image_url(soup: BeautifulSoup, page_url: str, doctor_name: str) -> str:
    candidates = []

    # 1) Look for images inside likely profile/header containers first
    preferred_containers = soup.select(
        ".doctor, .profile, .perfil, .medico, .content, .entry-content, .post, .single, .page"
    )

    seen = set()

    for container in preferred_containers:
        for img in container.find_all("img", src=True):
            src = img["src"].strip()
            if not src:
                continue
            absolute_url = urljoin(page_url, src)
            if absolute_url in seen:
                continue
            seen.add(absolute_url)

            score = score_image_candidate(img, absolute_url, doctor_name)
            candidates.append((score, absolute_url))

    # 2) Fallback: inspect all images on page
    for img in soup.find_all("img", src=True):
        src = img["src"].strip()
        if not src:
            continue
        absolute_url = urljoin(page_url, src)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)

        score = score_image_candidate(img, absolute_url, doctor_name)
        candidates.append((score, absolute_url))

    if not candidates:
        return ""

    candidates.sort(key=lambda item: item[0], reverse=True)

    best_score, best_url = candidates[0]
    if best_score < 0:
        return ""

    return best_url


def parse_profile_page(url: str, html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text(" ", strip=True)

    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)
    elif soup.title:
        name = soup.title.get_text(" ", strip=True).split(" en Médicos de El Salvador")[0].strip()
    else:
        return None

    name_lower = name.lower()
    if not (name_lower.startswith("dr.") or name_lower.startswith("dra.")):
        return None

    image_url = extract_doctor_image_url(soup, url, name)

    return {
        "name": name,
        "profile_url": url,
        "image_url": image_url,
        "raw_text": page_text
    }


def main():
    all_profile_links = set()
    all_listing_pages = set()

    for path in START_PATHS:
        start_url = urljoin(BASE_URL, path)
        listing_pages, profile_links = collect_listing_and_pagination(start_url)

        all_listing_pages.update(listing_pages)
        all_profile_links.update(profile_links)

    print(f"Collected {len(all_listing_pages)} listing pages")
    print(f"Collected {len(all_profile_links)} candidate profile links")

    if not all_profile_links:
        print("No profile links found. Check selectors or network access.")
        return

    records = []
    skipped = 0

    for idx, profile_url in enumerate(sorted(all_profile_links), start=1):
        print(f"[{idx}/{len(all_profile_links)}] Fetching profile: {profile_url}")
        html = fetch(profile_url)
        if not html:
            continue

        provider = parse_profile_page(profile_url, html)
        if provider is None:
            skipped += 1
            continue

        records.append(provider)
        time.sleep(0.5)

    with open("raw_providers.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(records)} doctor records to raw_providers.json")
    print(f"Skipped {skipped} non-doctor/clinic/association pages")


if __name__ == "__main__":
    main()
import datetime
import json
import os
import re
import string
from html import unescape
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

import jwt
import requests
import spotipy
from bs4 import BeautifulSoup
from dateutil.parser import parse
from python_graphql_client import GraphqlClient
from spotipy.oauth2 import SpotifyClientCredentials

from app.config import Config
from app.utils.common import Common


class Parser:
    @staticmethod
    def get_encoded_token(user_id, days=1):
        """Generates JWT token

        Args:
            user_id (string): User Id

        Raises:
            Exception: Any

        Returns:
            _type_: Jwt Token
        """
        try:
            # Generate a JWT token
            jwt_payload = {
                "id": str(user_id),
                # CHANGE NUMBER OF DAYS LATER
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days),
            }
            jwt_secret_key = Config.JWT_SECRET_KEY
            jwt_algorithm = "HS256"  # Use the desired JWT algorithm
            jwt_token = jwt.encode(jwt_payload, jwt_secret_key, algorithm=jwt_algorithm)

            return jwt_token
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def get_decoded_token(jwt_token):
        """
        The function `get_decoded_token` decodes a JWT token using a secret key and returns the decoded
        output, or None if an exception occurs.

        Args:
          jwt_token: The `jwt_token` parameter is the JSON Web Token (JWT) that needs to be decoded.

        Returns:
          the decoded token if it is successfully decoded using the provided secret key and algorithm.
        If there is an exception during the decoding process, the function returns None.
        """
        try:
            jwt_secret_key = Config.JWT_SECRET_KEY
            jwt_algorithm = "HS256"
            output = jwt.decode(
                jwt_token, key=jwt_secret_key, algorithms=[jwt_algorithm]
            )

            return output
        except Exception as e:
            Common.exception_details("Parser.get_decoded_token", e)
            return None

    @staticmethod
    def clean_input(input_str):
        """
        The clean_input function takes a string as input and returns the same string with leading and trailing whitespace removed.
            It also converts all characters to lowercase.

        Args:
            input_str: Store the string that is passed into the function

        Returns:
            A string with white spaces removed from the start and end of the string
        """

        return input_str.strip().lower()

    def get_open_graph(self, url):
        """
        The function `get_open_graph` retrieves Open Graph meta tags (title, description, and image) from
        a given URL.

        Args:
          url: The `url` parameter is the URL of the webpage from which you want to extract Open Graph
        tags.

        Returns:
          a list of dictionaries. Each dictionary contains the Open Graph tag name as the key and the
        corresponding content as the value. The Open Graph tags being retrieved are "og:title",
        "og:description", and "og:image". If any of these tags are not found in the HTML, an empty
        string is returned for that tag.
        """
        try:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")
            meta = soup.find_all("meta")
            result = []
            ogTags = ["og:title", "og:description", "og:image"]

            for ogTag in ogTags:
                if soup.findAll("meta", property=ogTag):
                    ogTagContent = soup.find("meta", property=ogTag)["content"]
                    ogItem = {ogTag: ogTagContent}
                    result.append(ogItem)
                else:
                    result.append({ogTag: ""})
            if result[1]["og:description"] == "":
                for tag in meta:
                    if "name" in tag.attrs.keys() and tag.attrs[
                        "name"
                    ].strip().lower() in ["description"]:
                        result[1]["og:description"] = tag.attrs["content"]

            return result
        except Exception as e:
            print("Exception in : Parser.get_open_graph() !")
            raise Exception(e)

    def get_podcast_info(self, url):
        VERBOSE_DEFAULT = False

        SPOTIFY_CLIENT_ID = Config.SPOTIFY_CLIENT_ID
        SPOTIFY_CLIENT_SECRET = Config.SPOTIFY_CLIENT_SECRET
        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
            )
        )
        RE_EP = re.compile("^\#?\d+|(?:ep|episode|EP|episode)\s?\#?\d+")
        RE_NO_KEYWORDS = re.compile("\s+\|\s+")
        ITUNES_THUMBS = [
            "artworkUrl600",
            "artworkUrl160",
            "artworkUrl100",
            "artworkUrl60",
        ]

        def itunes_lookup(podcastId, limit=200, sort="recent"):
            """
            Returns all episodes of podcast with ID `podcastId`
            """

            # Query for podcast info
            payload = {
                "id": podcastId,
                "media": "podcast",
                "entity": "podcastEpisode",
                "sort": sort,
                "limit": min(limit, 200),
            }
            url = "https://itunes.apple.com/lookup"
            try:
                response = requests.get(url, params=payload)
                response.raise_for_status()
            except requests.RequestException:
                # print(f"iTunes Lookup API: Failed for {podcastId}")
                return []

            data = response.json()
            return data["results"]

        def transform_itunes(episode, metadata, search_term=None):
            db_item = self._db_item(media_type="audio", tags="podcast")

            authors = metadata["authors"] or episode.get("collectionName", "")
            episode_thumbnail = self._best_thumbnail(episode, ITUNES_THUMBS)

            db_item["title"] = episode.get("trackName")
            db_item["thumbnail"] = (
                metadata["thumbnail"]
                if metadata["thumbnail"] != ""
                else episode_thumbnail
            )
            db_item["description"] = self._clean_html(episode.get("description", ""))
            db_item["authors"].append(authors)
            db_item["metadata"]["audio_file"] = episode.get("episodeUrl")
            db_item["metadata"]["podcast_title"] = episode.get("collectionName")
            db_item["metadata"]["url"] = episode.get("trackViewUrl")
            db_item["metadata"]["tag"] = (
                [search_term.strip().lower()] if isinstance(search_term, str) else []
            )
            db_item["metadata"]["additional_links"] = {
                "itunes_url": episode.get("trackViewUrl"),
                "spotify_url": None,
            }
            db_item["metadata"]["podcast_description"] = metadata.get(
                "podcast_description"
            )
            db_item["metadata"]["total_episodes"] = metadata.get("total_episodes")
            db_item["metadata"]["rating"] = metadata.get("rating")
            db_item["metadata"]["rating_count"] = metadata.get("rating_count")
            db_item["metadata"]["podcast_id"] = {
                "itunes_id": episode.get("collectionId"),
                "spotify_id": None,
            }
            db_item["metadata"]["id"] = {
                "itunes_id": episode.get("trackId"),
                "spotify_id": None,
            }
            db_item["metadata"]["episode_thumbnail"] = episode_thumbnail

            db_item["original"].append(episode)
            db_item["publishedDate"] = self._standard_date(episode.get("releaseDate"))

            calculate_score_podcast(db_item)

            return db_item

        def add_spotify_data(db_item, spotify_episode):
            # Add Spotify URL
            db_item["metadata"]["additional_links"]["spotify_url"] = spotify_episode[
                "external_urls"
            ]["spotify"]
            # Add Spotify ID
            db_item["metadata"]["id"]["spotify_id"] = spotify_episode.get("id")
            db_item["metadata"]["podcast_id"]["spotify_id"] = spotify_episode.get(
                "show", {}
            ).get("id")
            # Add Spotify result to original
            db_item["original"].append(spotify_episode)
            # Add description if missing
            if not db_item.get("description") or db_item["description"] == "":
                db_item["description"] = spotify_episode.get("description", "")
                # Add total_episodes if missing
            if not db_item.get("total_episodes") and "show" in spotify_episode:
                db_item["total_episodes"] = spotify_episode["show"]["total_episodes"]

        def transform_spotify(episode, search_term=None):
            db_item = self._db_item(media_type="audio", tags="podcast")
            show = episode.get("show", {})

            db_item["title"] = episode.get("name")
            db_item["thumbnail"] = show["images"][0]["url"]
            db_item["description"] = self._clean_html(episode.get("description", ""))
            db_item["authors"].append(show.get("publisher", ""))
            db_item["metadata"]["audio_file"] = episode.get("audio_preview_url")
            db_item["metadata"]["podcast_title"] = show.get("name")
            db_item["metadata"]["url"] = episode["external_urls"]["spotify"]
            db_item["metadata"]["tag"] = (
                [search_term.strip().lower()] if isinstance(search_term, str) else []
            )
            db_item["metadata"]["additional_links"] = {
                "itunes_url": None,
                "spotify_url": episode["external_urls"]["spotify"],
            }
            db_item["metadata"]["podcast_description"] = self._clean_html(
                show.get("description", "")
            )
            db_item["metadata"]["total_episodes"] = show.get("total_episodes")
            db_item["metadata"]["rating"] = 0.0
            db_item["metadata"]["rating_count"] = 0
            db_item["metadata"]["podcast_id"] = {
                "itunes_id": None,
                "spotify_id": show.get("id"),
            }
            db_item["metadata"]["id"] = {
                "itunes_id": None,
                "spotify_id": episode.get("id"),
            }
            db_item["metadata"]["episode_thumbnail"] = episode["images"][0]["url"]
            db_item["original"].append(episode)
            db_item["publishedDate"] = self._standard_date(episode.get("release_date"))

            return db_item

        def add_itunes_data(db_item, itunes_episode):
            podcast_id = itunes_episode["collectionId"]
            metadata = scrape_itunes_metadata(podcast_id)
            db_item["metadata"]["additional_links"]["itunes_url"] = itunes_episode.get(
                "trackViewUrl"
            )
            db_item["metadata"]["rating"] = metadata.get("rating")
            db_item["metadata"]["rating_count"] = metadata.get("rating_count")
            db_item["metadata"]["podcast_id"]["itunes_id"] = podcast_id
            db_item["metadata"]["id"]["itunes_id"] = itunes_episode.get("trackId")
            db_item["metadata"]["audio_file"] = itunes_episode.get(
                "episodeUrl", db_item["metadata"]["audio_file"]
            )
            db_item["original"].append(itunes_episode)
            calculate_score_podcast(db_item)

        def spotify_find_episodes(title, podcast, verbose=VERBOSE_DEFAULT):
            """
            Searches Spotify for podcast episode with given title and podcast name
            accounts for some variation in titles and podcast names
            returns matching episode object from Spotify
            """
            if verbose:
                action_str = f"Searching for: {title} | {podcast}"
                # print("\n", action_str)
                # print("-" * len(action_str))

            # Get full info of episodes with matching titles
            try:
                matching_ids = spotify_matching_episode_ids(title, podcast, verbose)
                matching_episodes = (
                    spotify_get_episodes(matching_ids) if len(matching_ids) > 0 else []
                )
            except Exception as e:
                print("Exception in : Parser.get_open_graph() !")
                raise Exception(e)

            # For each matching episode, check podcast name
            for episode in matching_episodes:
                # url = episode['external_urls']['spotify']
                title_spotify = episode["name"]
                podcast_spotify = episode["show"]["name"]
                publisher = episode["show"]["publisher"]

                # if verbose:
                #     print(title_spotify, " | ", podcast_spotify)

                # If podcast name matches, update item and stop checking for this item
                if match_podcast(podcast, podcast_spotify, publisher):
                    # if verbose: print("Found it!")
                    return episode

            return None

        def spotify_matching_episode_ids(title, podcast, verbose=VERBOSE_DEFAULT):
            """
            Searches Spotify for podcast with given title and podcast name,
            accounts for some variation in episode title,
            returns list of Spotify IDs of episodes that are possible matches
            """

            try:
                # Better results when searching for both episode and podcast names
                query = title + " " + podcast
                # Restrict query to 100 characters by removing full words
                while len(query) > 100:
                    query = query.rsplit(" ", maxsplit=1)[0]
                # Get results
                results = sp.search(
                    q=query, type="episode", limit=10, offset=0, market="US"
                )
            except spotipy.SpotifyException as e:
                print(e.msg, e.reason)
                if e.http_status == 429:
                    raise Exception("Spotify Quota Exceeded")
                return []

            # Loop through list and make list of possible matches
            matches = []
            for episode in results["episodes"]["items"]:
                spotify_title = episode["name"]
                if match_title(title, podcast, spotify_title):
                    matches.append(episode["id"])
                    # if verbose:
                    #     print("✔️ ", episode['name'])
                # elif verbose:
                #     print("X ", episode['name'])

            return matches

        def match_title(title, podcast, spotify_title):
            """Match episode titles accounting for subtle differences"""

            # Normalize by lowering case and removing punctuation
            title = title.strip().casefold()
            title = title.translate(str.maketrans("", "", string.punctuation))
            spotify_title = spotify_title.strip().casefold()
            spotify_title = spotify_title.translate(
                str.maketrans("", "", string.punctuation)
            )
            podcast = podcast.strip().casefold()
            podcast = podcast.translate(str.maketrans("", "", string.punctuation))

            # 1. Spotify title is the same as item title
            if title == spotify_title:
                return True
            # 2. Spotify title includes both title of epsiode and name of podcast
            elif title in spotify_title and podcast in spotify_title:
                return True

            # Remove episode numbers from titles
            spotify_title_no_ep = re.sub(RE_EP, "", spotify_title).strip()
            title_no_ep = re.sub(RE_EP, "", title).strip()
            # 3. After removing episode number, Spotify title is the same as item title
            if title == spotify_title_no_ep:
                return True
            # 4. After removing episode number, Spotify title includes both title of epsiode and name of podcast
            elif title_no_ep in spotify_title_no_ep and podcast in spotify_title_no_ep:
                return True

            return False

        def spotify_get_episodes(ids):
            """
            Get episode objects from Spotify for each id
            """
            try:
                results = sp.episodes(ids, market="US")
            except spotipy.SpotifyException as e:
                raise Exception(e.http_status, e.msg)
            else:
                return results["episodes"]

        def match_podcast(podcast, spotify_podcast, publisher=None):
            """Match podcast names accounting for subtle differences"""

            # Normalize by lowering case
            podcast = podcast.strip().casefold()
            spotify_podcast = spotify_podcast.strip().casefold()
            publisher = publisher.strip().casefold() if publisher else None

            # 1. Spotify's podcast name is same as podcast name
            if podcast == spotify_podcast:
                return True
            # 2. Podcast name includes Spotify's podcast name and publisher
            if publisher and (spotify_podcast in podcast and publisher in podcast):
                return True
            # 3. After removing punctuation, Spotify's podcast name is same as podcast name
            if podcast.translate(
                str.maketrans("", "", string.punctuation)
            ) == spotify_podcast.translate(str.maketrans("", "", string.punctuation)):
                return True

            # 4. After removing right-most tagline indicated by " - "
            #    Spotify's podcast name is same as podcast name
            podcast_no_tag = podcast.rsplit(" - ", maxsplit=1)[0]
            spotify_podcast_no_tag = spotify_podcast.rsplit(" - ", maxsplit=1)[0]
            if podcast_no_tag == spotify_podcast_no_tag:
                return True

            # 5. After removing all keywords indicated by " | "
            #    Spotify's podcast name is same as podcast name
            podcast_no_keys = re.split(RE_NO_KEYWORDS, podcast)[0]
            spotify_podcast_no_keys = re.split(RE_NO_KEYWORDS, spotify_podcast)[0]
            if podcast_no_keys == spotify_podcast_no_keys:
                return True

            return False

        def itunes_search_podcasts(
            search_term, limit=10, search_type="podcastEpisode", attribute=None
        ):
            """
            Searches podcasts for given search term using iTunes Search API
            https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/Searching.html#//apple_ref/doc/uid/TP40017632-CH5-SW1
            and outputs list (default count of 10) of `title`, `url`, `feedUrl` (for RSS),
            `trackName`, `trackUrl` are relevant if searching by episode instead of entire podcast
            """
            if search_type not in ["podcast", "podcastEpisode"]:
                # print("Invalid search type")
                return None

            # Query for podcast info
            payload = {
                "term": search_term,
                "media": "podcast",
                "entity": search_type,
                "limit": limit,
            }
            if attribute:
                if attribute in [
                    "titleTerm",
                    "languageTerm",
                    "authorTerm",
                    "genreIndex",
                    "artistTerm",
                    "ratingIndex",
                    "keywordsTerm",
                    "descriptionTerm",
                ]:
                    payload["attribute"] = attribute

            url = "https://itunes.apple.com/search"
            try:
                response = requests.get(url, params=payload)
                response.raise_for_status()

            except requests.exceptions.ConnectionError as e:
                if e.errno == -2:
                    raise Exception("iTunes Search: Too many retries")
                raise Exception(e)

            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    raise Exception(
                        "iTunes Search: Quota exceeded for iTunes Search API"
                    )
                return []

            except Exception as e:
                print(e)
                return []

            # Parse response
            data = response.json()
            return data["results"]

        def itunes_find_episode(
            title, podcast, publisher=None, verbose=VERBOSE_DEFAULT
        ):
            if verbose:
                action_str = f"Searching for: {title} | {podcast}"
                # print("\n", action_str)
                # print("-" * len(action_str))

            search_term = title + " " + podcast
            itunes_results = itunes_search_podcasts(
                search_term, limit=10, search_type="podcastEpisode"
            )
            if itunes_results == []:
                itunes_results = itunes_search_podcasts(
                    title, limit=10, search_type="podcastEpisode", attribute="titleTerm"
                )
            # Loop through list of possible matches
            for result in itunes_results:
                title_itunes = result["trackName"]
                podcast_itunes = result["collectionName"]

                if match_title(title, podcast, title_itunes):
                    # if verbose: print("✔️ ", title_itunes, " | ", podcast_itunes)
                    # If podcast name matches, check podcast name
                    if match_podcast(podcast, podcast_itunes, publisher):
                        # if verbose: print("Found it!")
                        return result
                # elif verbose:
                #     print("X ", title_itunes, " | ", podcast_itunes)

            return None

        def scrape_itunes_metadata(podcast_id, show={}):
            # default result
            metadata = {
                "podcast_description": None,
                "rating": 0.0,
                "rating_count": 0,
                "total_episodes": show.get("trackCount"),
                "authors": show.get("artistName"),
                "thumbnail": self._best_thumbnail(show, ITUNES_THUMBS),
            }
            # Check podcast_id
            if isinstance(podcast_id, int):
                podcast_id = str(podcast_id)
            elif not isinstance(podcast_id, str):
                return metadata
                # Construct URL
            base_url = "https://podcasts.apple.com/us/podcast/id"
            url = base_url + podcast_id
            # Get podcast page
            try:
                response = requests.get(url)
                response.raise_for_status()
            except Exception as e:
                print(e)
                return metadata

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract description
            section = soup.find("section", class_="product-hero-desc__section")
            if section:
                metadata["podcast_description"] = section.text.strip()
            # Extract element containing ratings
            rating_elems = soup.find_all(
                "figcaption", class_="we-rating-count star-rating__count"
            )
            for elem in rating_elems:
                ratings = elem.text.split(" • ")
                if len(ratings) == 2 and " Rating" in ratings[1]:
                    # Return float value of rating and int value of number of ratings
                    try:
                        rating = float(ratings[0].strip())
                        rating_count_str = (
                            ratings[1]
                            .replace(" Ratings", "")
                            .replace(" Rating", "")
                            .strip()
                        )
                        if "K" in rating_count_str:
                            rating_count_str = rating_count_str.replace("K", "")
                            rating_count = int(float(rating_count_str) * 1000)
                        else:
                            rating_count = int(rating_count_str)
                    except ValueError as e:
                        print(e)
                    else:
                        metadata["rating"] = rating
                        metadata["rating_count"] = rating_count

            return metadata

        def calculate_score_podcast(db_item, score=0):
            metadata = db_item["metadata"]

            if metadata["rating"] > 4.5:
                if metadata["rating_count"] >= 2000:
                    score += 5
                elif metadata["rating_count"] >= 1000:
                    score += 4
                elif metadata["rating_count"] >= 500:
                    score += 3
                else:
                    score += 2

            elif metadata["rating"] > 4.0:
                if metadata["rating_count"] >= 2000:
                    score += 4
                elif metadata["rating_count"] >= 1000:
                    score += 3
                elif metadata["rating_count"] >= 500:
                    score += 2
                else:
                    score += 1

            elif metadata["rating"] > 3.5:
                if metadata["rating_count"] >= 2000:
                    score += 3
                elif metadata["rating_count"] >= 1000:
                    score += 2
                elif metadata["rating_count"] >= 500:
                    score += 1
                else:
                    score += 0

            # Total episodes
            if metadata["total_episodes"] > 500:
                score += 3
            elif metadata["total_episodes"] > 300:
                score += 2
            elif metadata["total_episodes"] > 100:
                score += 1

            pub_date = datetime.datetime.strptime(db_item["publishedDate"], "%Y-%m-%d")
            today = datetime.datetime.today()
            days_since_pub = (today - pub_date).days
            if days_since_pub > 730:
                score += -3
            elif days_since_pub > 365:
                score += -2
            elif days_since_pub > 180:
                score += -1

            db_item["score"] = score

        def scrape_google_podcasts(url):
            # Get podcast page
            try:
                response = requests.get(url)
                response.raise_for_status()
            except Exception as e:
                raise Exception(f"Failed fetching URL {url}: {e}")

            soup = BeautifulSoup(response.content, "html.parser")

            try:
                podcast_path, episode_id = url.rsplit("/episode/", maxsplit=1)
                _, podcast_id = podcast_path.rsplit("/", maxsplit=1)
            except ValueError:
                raise Exception("Google Podcast URL does not point to a episode")

            try:
                div_title = soup.find("div", class_="wv3SK")
                a_podcast = soup.find("a", class_="ik7nMd")
                div_publisher = soup.find("div", class_="J3Ov7d")
                if not div_title or not a_podcast:
                    unavailable = soup.find(
                        text="This podcast is not available or not yet published"
                    )
                    if unavailable:
                        raise Exception(f"Podcast not available on Google: {url}")
                    else:
                        raise Exception("Scraping error")
                title = div_title.text.strip()
                podcast_title = a_podcast.text.strip()
                publisher = div_publisher.text.strip() if div_publisher else None
            except Exception as e:
                raise Exception(f"Scraping Google Podcast failed: {e}")

            return {
                "title": title,
                "podcast_title": podcast_title,
                "publisher": publisher,
                "episode_id": episode_id,
                "podcast_id": podcast_id,
            }

        try:
            # Check if URL is Spotify or iTunes
            if "podcasts.apple.com" in url:
                # 1. If iTunes, extract ID
                parsed_url = urlparse(url)
                split_path = parsed_url.path.rstrip("/").rsplit("/", maxsplit=2)
                if len(split_path) != 3 or "id" not in split_path[2]:
                    raise Exception("No iTunes ID for podcast found in URL")
                podcast_id = split_path[2].replace("id", "")
                title = split_path[1].replace("-", " ")

                queries = parse_qs(parsed_url.query)
                if not queries.get("i"):
                    raise Exception("No iTunes ID for podcast episode found in URL")
                itunes_id = int(queries["i"][0])

                # 2a. Get info about podcast from Apple
                itunes_results = itunes_lookup(podcast_id)
                if not itunes_results:
                    raise Exception(f"iTunes Lookup API: Failed for {podcast_id}")
                show = next(
                    (item for item in itunes_results if item["kind"] == "podcast"), {}
                )
                # 2b. Get matching episode having id `itunes_id` from results
                try:
                    episode = next(
                        result
                        for result in itunes_results
                        if result["trackId"] == itunes_id
                    )
                # If epsiode not
                except StopIteration:
                    if title == "podcast":
                        raise Exception(
                            f"iTunes Lookup API: Could not look up episode {itunes_id} without slug in URL"
                        )
                    itunes_results = itunes_search_podcasts(
                        title,
                        limit=10,
                        search_type="podcastEpisode",
                        attribute="titleTerm",
                    )
                    try:
                        episode = next(
                            result
                            for result in itunes_results
                            if result["trackId"] == itunes_id
                        )
                    except Exception:
                        raise Exception(
                            f"iTunes Lookup API: Could not look up episode {itunes_id}"
                        )

                        # 3. Scrape ratings and other metadata
                metadata = scrape_itunes_metadata(podcast_id, show)

                # 4. Transform result
                item = transform_itunes(episode, metadata)

                # 5. Get Spotify URL
                try:
                    spotify_episode = spotify_find_episodes(
                        title=item["title"], podcast=item["metadata"]["podcast_title"]
                    )
                except Exception as e:
                    print(e)
                else:
                    if spotify_episode:
                        add_spotify_data(item, spotify_episode)

            if "open.spotify.com" in url:
                # 1. If Spotify, extract ID
                parsed_url = urlparse(url)
                split_path = parsed_url.path.rsplit("/", maxsplit=1)
                if len(split_path) != 2:
                    raise Exception("No Spotify ID found in URL")
                if split_path[0] != "/episode":
                    raise Exception("Spotify URL not for podcast episode")
                spotify_id = split_path[1]

                # 2. Get info about episode from podcast
                episode = spotify_get_episodes([spotify_id])[0]
                if not episode:
                    raise Exception(f"Spotify episode with ID {spotify_id} not found")
                # 3. Transform result
                item = transform_spotify(episode)
                # 4. Get iTunes URL
                episode_name = item["title"]
                podcast_name = item["metadata"]["podcast_title"]
                publisher = item["authors"][0]

                try:
                    itunes_episode = itunes_find_episode(
                        title=episode_name, podcast=podcast_name, publisher=publisher
                    )
                except Exception as e:
                    print(e)
                # 5. Update metadata if iTunes URL found
                if itunes_episode:
                    add_itunes_data(item, itunes_episode)
                else:
                    calculate_score_podcast(item, score=3)

            if "podcasts.google.com/feed/" in url:
                ## Searching iTunes then Spotify

                # 1. Scrape page to get episode_name, podcast_name and publisher/author
                url = self._remove_queries(url.rstrip("/"))
                result = scrape_google_podcasts(url)

                # 2. Search iTunes
                itunes_episode = itunes_find_episode(
                    title=result["title"],
                    podcast=result["podcast_title"],
                    publisher=result["publisher"],
                )

                # 3. Scrape ratings and other metadata
                podcast_id = itunes_episode["collectionId"]
                itunes_results = itunes_lookup(podcast_id, limit=1)
                if itunes_results:
                    show = next(
                        (item for item in itunes_results if item["kind"] == "podcast"),
                        {},
                    )
                metadata = scrape_itunes_metadata(podcast_id, show)

                # 4. Transform result
                item = transform_itunes(itunes_episode, metadata)

                # 5. Search Spotify and append data
                try:
                    spotify_episode = spotify_find_episodes(
                        title=item["title"], podcast=item["metadata"]["podcast_title"]
                    )
                except Exception as e:
                    print(e)
                else:
                    if spotify_episode:
                        add_spotify_data(item, spotify_episode)

                # 6. Add Google URL
                item["metadata"]["additional_links"]["google_url"] = url
                item["metadata"]["id"]["google_id"] = result["episode_id"]
                item["metadata"]["podcast_id"]["google_id"] = result["podcast_id"]

            return item

        except Exception as e:
            print("Exception in : Parser.get_podcast_info() !")
            return None

    def get_book_info(self, url):
        """
        The function `get_book_info` retrieves information about a book from the Google Books API based
        on a given URL.

        Args:
          url: The `url` parameter is the URL of a book on Google Books.

        Returns:
          the book information in the form of a dictionary.
        """
        API_KEY = Config.GOOGLEBOOKS_API_KEY
        BOOK_THUMBS = [
            "extraLarge",
            "large",
            "medium",
            "small",
            "thumbnail",
            "smallThumbnail",
        ]

        def get_googlebooks_volume(url):
            # Extract YouTube ID
            parsed_url = urlparse(url)
            queries = parse_qs(parsed_url.query)
            ids = queries.get("id")
            if not ids:
                paths = parsed_url.path.rstrip("/").split("/")
                ids = [paths[-1]]

            google_url = "https://www.googleapis.com/books/v1/volumes/" + ids[0]
            payload = {
                "key": API_KEY,
            }
            # Make request
            payload_str = urlencode(payload, safe=":+")
            try:
                response = requests.get(google_url, params=payload_str)
                response.raise_for_status()
            except requests.RequestException as e:
                raise Exception(
                    f"Unable to fetch data for Google Books ID {ids[0]}: {e}"
                )

            data = response.json()
            return data

        def transform_book(item):
            """Transform to KI item"""
            db_item = self._db_item(media_type="books", tags="books")
            volume = item["volumeInfo"]

            if not volume.get("description") or volume["description"] == "":
                raise Exception("No description found")

            authors = [a.strip() for a in volume.get("authors", []) if a.strip() != ""]

            db_item["title"] = volume["title"]
            db_item["thumbnail"] = self._best_thumbnail(
                volume.get("imageLinks"), BOOK_THUMBS
            )
            db_item["description"] = self._clean_html(volume.get("description", ""))
            db_item["authors"] = authors
            db_item["metadata"]["id"] = item["id"]
            db_item["metadata"]["url"] = volume["previewLink"]
            db_item["metadata"]["category"] = volume.get("categories", [])
            db_item["metadata"]["rating"] = volume.get("averageRating", 0)
            db_item["metadata"]["rating_count"] = volume.get("ratingsCount", 0)
            db_item["original"].append(item)
            db_item["publishedDate"] = self._standard_date(volume.get("publishedDate"))

            return db_item

        try:
            book = get_googlebooks_volume(url)
            if not book:
                raise Exception(f"No results found for", url)
            item = transform_book(book)
            return item

        except Exception as e:
            print("Exception in : Parser.get_book_info() !")
            raise None

    def get_youtube_info(self, url):
        """
        The `get_youtube_info` function retrieves information about a specific YouTube video identified
        by its URL.

        Args:
          url: The `url` parameter is the URL of a YouTube video.

        Returns:
          an item containing information about a YouTube video.
        """
        API_KEY = Config.YOUTUBE_API_KEY
        YOUTUBE_THUMBS = ["high", "maxres", "standard", "medium", "default"]

        def get_video_info(url):
            """
            Retrieves information about a specific video identified by id parameter
            https://developers.google.com/youtube/v3/docs/videos/list
            """
            # Extract YouTube ID
            parsed_url = urlparse(url)
            queries = parse_qs(parsed_url.query)
            ids = queries.get("v")
            if not ids:
                raise Exception(f"YouTube ID not found in url", url)
            # Construct request URL
            payload = {
                "part": "snippet,statistics",
                "id": ids[0],
                "key": API_KEY,
            }
            google_url = "https://www.googleapis.com/youtube/v3/videos"
            payload_str = urlencode(payload, safe=":+")
            # Make Request
            try:
                response = requests.get(google_url, params=payload_str)
                response.raise_for_status()
            except requests.RequestException as e:
                raise Exception(
                    f"Unable to fetch data for YouTube video ID {payload['id']}: {e}"
                )
            # Parse response
            data = response.json()
            result = next((item for item in data["items"]), None)
            return result

        def transform_youtube(item):
            """Transform to KI item"""
            db_item = self._db_item(media_type="video", tags="youtube")
            snippet = item["snippet"]
            statistics = item["statistics"]

            db_item["title"] = snippet.get("title")
            db_item["thumbnail"] = self._best_thumbnail(
                snippet.get("thumbnails"), YOUTUBE_THUMBS, key="url"
            )
            db_item["description"] = self._clean_html(snippet.get("description", ""))
            db_item["authors"].append(snippet.get("channelTitle", ""))
            db_item["metadata"]["id"] = item["id"]
            db_item["metadata"]["url"] = f"https://www.youtube.com/watch?v={item['id']}"
            db_item["metadata"]["comment_count"] = int(
                statistics.get("commentCount", 0)
            )
            db_item["metadata"]["favorite_count"] = int(
                statistics.get("favoriteCount", 0)
            )
            db_item["metadata"]["like_count"] = int(statistics.get("likeCount", 0))
            db_item["metadata"]["view_count"] = int(statistics.get("viewCount", 0))
            db_item["original"].append(item)
            db_item["publishedDate"] = self._standard_date(snippet.get("publishedAt"))

            return db_item

        try:
            video = get_video_info(url)
            if not video:
                raise Exception(f"No results found for", url)
            item = transform_youtube(video)

            return item

        except Exception as e:
            print("Exception in : Parser.get_youtube_info() !")
            return None

    def get_research_info(self, url):
        """
        The `get_research_info` function retrieves research information from either PubMed or
        ScienceDirect based on the provided URL.

        Args:
          url: The `url` parameter is a string that represents the URL of a research article. It can be
        from either PubMed or ScienceDirect.

        Returns:
          The function `get_research_info` returns an item containing information about a research
        article.
        """
        API_KEY = Config.ELSEVIER_API_KEY

        def get_pubmed(url):
            # Extract ID
            parsed_url = urlparse(url)
            try:
                pmid = parsed_url[2].replace("/", "")
            except Exception:
                raise Exception("Could not get PubMed ID from", url, e)

            API_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            payload = {"db": "pubmed", "retmode": "xml", "id": pmid}
            # Make Request
            try:
                response = requests.get(API_url, params=payload)
                response.raise_for_status()
            except requests.RequestException as e:
                raise Exception(f"Unable to fetch data for PubMed ID {pmid}: {e}")
            # Parse response
            return xmltodict.parse(response.text)

        def transform_pubmed(data):
            db_item = self._db_item(media_type="article", tags="research")
            try:
                medline = data["PubmedArticleSet"]["PubmedArticle"]["MedlineCitation"]
                article = medline["Article"]
                abstract_text = article["Abstract"]["AbstractText"]
                author_list = article["AuthorList"]["Author"]

                # Extract description
                description = ""
                if isinstance(abstract_text, str):
                    description = abstract_text
                elif isinstance(abstract_text, dict):
                    description = abstract_text.get("#text", "")
                elif isinstance(abstract_text, list):
                    description = "\n".join(
                        item.get("@Label", " ") + item.get("#text", " ")
                        for item in abstract_text
                    )
                # Extract all authors
                if isinstance(author_list, dict):
                    author_list = [author_list]
                authors = []
                for author in author_list:
                    a = author.get("ForeName", "") + " " + author.get("LastName", "")
                    a = a.strip()
                    if a != "":
                        authors.append(a)
                        # Extract PubDate
                date_list = data["PubmedArticleSet"]["PubmedArticle"]["PubmedData"][
                    "History"
                ]["PubMedPubDate"]
                date_list = date_list if isinstance(date_list, list) else [date_list]
                pub_date_dict = next(
                    (item for item in date_list if item["@PubStatus"] == "pubmed"), {}
                )
                pub_date = datetime.date(
                    year=int(pub_date_dict["Year"]),
                    month=int(pub_date_dict.get("Month", 0)),
                    day=int(pub_date_dict.get("Day", 0)),
                ).isoformat()
                # Extract keywords
                keywords = [
                    item["#text"]
                    for item in medline.get("KeywordList", {}).get("Keyword", [])
                ]

                db_item["title"] = self._clean_html(article["ArticleTitle"])
                db_item["description"] = self._clean_html(description)
                db_item["authors"] = authors
                db_item["metadata"]["url"] = (
                    "https://pubmed.ncbi.nlm.nih.gov/" + medline["PMID"]["#text"]
                )
                db_item["metadata"]["id"] = int(medline["PMID"]["#text"])
                db_item["metadata"]["citations"] = ""
                db_item["original"].append(medline)
                db_item["publishedDate"] = pub_date

            except Exception as e:
                raise Exception(f"Could not transform PubMed article. {type(e)}: {e}")

            return db_item

        def get_sciencedirect(url):
            # Extract ID
            try:
                pii = url.rstrip("/").split("pii/")[1]
            except Exception as e:
                raise Exception("Could not get PubMed ID from", url, e)

                # Construct request URL
            API_url = "https://api.elsevier.com/content/article/pii/" + pii
            payload = {
                "apiKey": API_KEY,
                "httpAccept": "application/json",
            }
            # Get response
            try:
                response = requests.get(API_url, params=payload)
                response.raise_for_status()
            # Handle errors
            except requests.RequestException as e:
                if response.status_code == 429:
                    raise Exception("Elsevier API Quota exceeded")
                elif response.status_code == 400:
                    raise Exception(f"Invalid PII/userroutesation ID {id}")
                elif response.status_code == 404:
                    raise Exception(f"Resource not found for {id}")
                else:
                    raise Exception(f"Unable to fetch article {id}: {e}")
            # Get JSON response
            data = response.json()
            # Check key
            if "full-text-retrieval-response" not in data:
                raise Exception(f"Unable to parse article {id}")

            return data["full-text-retrieval-response"]

        def transform_scd(data):
            db_item = self._db_item(media_type="article", tags="research")
            coredata = data["coredata"]

            db_item["title"] = coredata["dc:title"]
            db_item["description"] = self._clean_html(
                coredata["dc:description"].strip()
            )
            db_item["authors"] = [
                creator["$"] for creator in coredata.get("dc:creator", [])
            ]
            db_item["metadata"]["url"] = next(
                (
                    link["@href"]
                    for link in coredata.get("link", [])
                    if link["@rel"] == "scidir"
                ),
                None,
            )
            db_item["metadata"]["id"] = url.split("pii/")[1]
            db_item["metadata"]["citations"] = ""
            db_item["original"].append(data)
            db_item["publishedDate"] = self._standard_date(
                coredata.get("prism:coverDate")
            )

            return db_item

        try:
            domain = urlparse(url).netloc

            if domain == "pubmed.ncbi.nlm.nih.gov":
                article = get_pubmed(url)
                if not article:
                    raise Exception(f"No results found for", url)
                item = transform_pubmed(article)

                return item

            else:
                article = get_sciencedirect(url)
                if not article:
                    raise Exception(f"No results found for", url)
                item = transform_scd(article)

                return item

        except Exception as e:
            print("Exception in : Parser.get_research_info() !")
            return None

    def get_tedtalks_info(self, url):
        """
        The `get_tedtalks_info` function retrieves information about a TED talk from a given URL and
        transforms it into a standardized format.

        Args:
          url: The `url` parameter is the URL of a TED Talk video.

        Returns:
          The function `get_tedtalks_info` returns an item containing information about a TED talk.
        """

        def get_tedtalk(url):
            talk_id = url.rstrip("/").rsplit("/", maxsplit=1)
            slug = talk_id[-1]
            client = GraphqlClient(endpoint="https://graphql.ted.com/")

            # Defined query and variables
            query = """
                query videoQuery($videoslug: String) {
                    video(slug:$videoslug) {
                        slug
                        id
                        title
                        playerData
                        description
                        curatorApproved
                        audioDownload
                        duration
                        audioInternalLanguageCode
                        hasTranslations
                        publishedAt
                        videoContext
                        recordedOn
                        language
                        viewedCount
                    }
                }
            """
            variables = {"videoslug": slug}

            result = client.execute(query=query, variables=variables)
            data = result.get("data", {})
            if data.get("video"):
                return data
            return None

        def transform_tedtalks(data):
            db_item = self._db_item(media_type="video", tags="tedtalks")
            video = data["video"]
            player = json.loads(video["playerData"])

            external = player.get("external", {})
            youtube_url = (
                "https://www.youtube.com/watch?v=" + external.get("code")
                if external.get("service") == "YouTube"
                else None
            )
            tag_string = player.get("targeting", {}).get("tag")
            tag = tag_string.split(",") if tag_string else []

            db_item["title"] = video["title"]
            db_item["thumbnail"] = player.get("thumb", "")
            db_item["description"] = self._clean_html(video["description"].strip())
            db_item["authors"].append(player.get("speaker", ""))
            db_item["metadata"]["id"] = video["id"]
            db_item["metadata"]["url"] = player.get("canonical", url)
            db_item["metadata"]["tag"] = tag
            # TODO: check fields
            db_item["metadata"]["video_length"] = str(
                datetime.timedelta(seconds=video.get("duration", 0))
            )
            db_item["metadata"]["additional_links"] = {"youtube_url": youtube_url}

            db_item["metadata"]["view_count"] = video.get("viewedCount", 0)
            db_item["original"].append(data)
            db_item["publishedDate"] = self._standard_date(video.get("publishedAt"))

            return db_item

        try:
            tedtalk = get_tedtalk(url)
            if not tedtalk:
                raise Exception(f"No results found for", url)
            item = transform_tedtalks(tedtalk)

            return item

        except Exception as e:
            print("Exception in : Parser.get_tedtalks_info() !")
            return None

    def get_kiid_from_url(self, url):
        """
        The function `get_kiid_from_url` takes a URL as input and returns the last part of the URL as
        the ki_id.

        Args:
          url: The `url` parameter is a string that represents a URL.

        Returns:
          the last element of the list 'words', which is the ki_id.
        """
        words = url.split("/")
        ki_id = words[len(words) - 1]
        return ki_id

    def not_supported_ki(self, url):
        """
        The function `not_supported_ki` retrieves Open Graph data from a given URL and transforms it
        into a standardized format.

        Args:
          url: The `url` parameter is a string that represents the URL of a webpage.

        Returns:
          the variable "item".
        """

        def get_opengraph(url):
            result = self.get_open_graph(url)
            # print(result)
            return result

        def transform_opengraph(data, url):
            db_item = self._db_item(media_type="", tags="")
            if data:
                for item in data:
                    if "og:title" in item.keys():
                        db_item["title"] = item["og:title"]
                    if "og:image" in item.keys():
                        db_item["thumbnail"] = item["og:image"]
                    if "og:description" in item.keys():
                        db_item["description"] = item["og:description"].strip()
            else:
                db_item["title"] = ""
                db_item["thumbnail"] = ""
                db_item["description"] = ""
            db_item["metadata"]["url"] = url
            db_item["original"].append(data)
            db_item["type"] = "Nonki"

            return db_item

        try:
            open_graph = get_opengraph(url)
            item = transform_opengraph(open_graph, url)

            return item

        except Exception as e:
            Common.exception_details("Parser.py : not_supported_ki", e)
            return None

    @staticmethod
    def _clean_html(raw_html):
        """
        Cleans HTML text by replacing with end-of-line, spaces and para tags
        with appropriate alternatives. Removes all other HTML tags `<...>`
        Unescapes remaining text.
        """
        if not isinstance(raw_html, str):
            return raw_html

        RE_TAG = re.compile("<.*?>")
        RE_SPACE_TAG = re.compile("&nbsp;")
        RE_EOL_TAG = re.compile("</p>|(<br>)+|(<br/>)+")

        temp = re.sub(RE_EOL_TAG, "\n", raw_html)
        temp = re.sub(RE_SPACE_TAG, " ", temp)
        temp = re.sub(RE_TAG, "", temp)
        clean_text = unescape(temp)
        return clean_text

    @staticmethod
    def _standard_date(pub_date):
        """Standardise date format"""
        if pub_date:
            try:
                # Date format: YYYY -> YYYY:01:01
                date = datetime.datetime.strptime(pub_date, "%Y")
                pub_date = date.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    # Check for timezones. #TODO: Account for more timezones
                    pub_date = pub_date.replace("EDT", "-0400")
                    pub_date = pub_date.replace("EST", "-0500")
                    pub_date = pub_date.replace("PST", "-0800")
                    pub_date = pub_date.replace("PDT", "-0700")
                    # Parse most known formats
                    date = parse(pub_date)
                    pub_date = date.strftime("%Y-%m-%d")
                except ValueError:
                    return None

        return pub_date

    @staticmethod
    def _remove_queries(url):
        """
        The function `_remove_queries` takes a URL as input and removes any query parameters and
        fragments from it.

        Args:
          url: The `url` parameter is a string representing a URL.

        Returns:
          the cleaned URL with the queries and fragments removed.
        """
        cleaned_url = urlunsplit(urlsplit(url)._replace(query="", fragment=""))
        return cleaned_url

    @staticmethod
    def _best_thumbnail(data, choices, key=None):
        """
        The function `_best_thumbnail` returns the best thumbnail from a given data dictionary based on
        a list of choices, with an optional key to access nested values.

        Args:
          data: The `data` parameter is a dictionary that contains the information from which we want to
        select the best thumbnail.
          choices: The `choices` parameter is a list of keys that will be checked in the `data`
        dictionary. These keys represent different options for the thumbnail. The function will iterate
        through the `choices` list and return the first non-empty and non-null value found in the `data`
        dictionary for any of
          key: The "key" parameter is an optional argument that specifies the key to use when retrieving
        the value from the dictionary. If provided, it will return the value associated with the
        specified key from the dictionary. If not provided, it will return the entire value associated
        with the first available choice in the "choices

        Returns:
          the value of the first non-empty and non-null choice in the data dictionary. If a key is
        provided, it returns the value of that key in the chosen choice. If no non-empty and non-null
        choice is found, it returns an empty string.
        """
        if isinstance(data, dict):
            for choice in choices:
                if choice in data and data[choice] is not None and data[choice] != "":
                    if key:
                        return data[choice][key]
                    return data[choice]
        return ""

    @staticmethod
    def _db_item(media_type=None, tags=None):
        """Common fields for KI database item"""
        db_item = {
            "title": None,
            "thumbnail": "",
            "description": None,
            "permission": "Global",
            "authors": [],
            "mediaType": media_type,
            "tags": tags,
            "type": "ki",
            "metadata": {
                "transcript": "",
            },
            "created": datetime.datetime.utcnow(),
            "createdBy": None,
            "updated": "",
            "isDeleted": False,
            "original": [],
            "publishedDate": None,
            "status": 2,
            "score": 0,
        }

        return db_item

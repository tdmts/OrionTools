"""Stage a Brightspace course export into _incoming/ so orion-convert can run per page.

    python ../OrionTools/orion.py import-brightspace export.zip
    python ../OrionTools/orion.py import-brightspace export.zip --dry-run
    python ../OrionTools/orion.py import-brightspace export.zip --only "Managed Switch"
    python ../OrionTools/orion.py import-brightspace export.zip --fetch-remote

Reads a Brightspace "Export Components" package or a Common Cartridge zip and
writes one raw HTML file per content topic into _incoming/, keeping the module
tree, the ordering and the original path in a header comment. Every image the
topics reference is copied out of the zip into img/ (deduplicated against the
images already in the repo) and the src is rewritten to a local relative path,
so no /content/enforced/ hotlink ever reaches a page.

Documents get the same treatment, whether they hang in the module tree as a
topic of their own or are linked from inside a page. Which extensions count as
a document is course config (import_brightspace.doc_exts): a datasheet PDF and
a code bundle everywhere, and in IR also RobotStudio and CAD files. A document
goes to datasheets/, unless its extension is in import_brightspace.start_exts,
in which case it is something a student opens in a tool (RobotStudio,
In-Sight) and goes to startbestanden/. Lecture slides are left on Brightspace
on purpose, see the comment on doc_exts in config.py.

**The manifest is the only authority on what the course contains.** A D2L export
carries the org unit's entire Manage Files area, not just the files a topic links,
and that area never empties: a Course Copy drags the source course's files along
even when you deselect its topics, and deleting a topic leaves its file behind.
The DeN export is full of material from a programming course as a result, and
the ICEES export carries a stray "Een map of bestand verwijderen (rm) 2.html" in
the package root and an "embedded/" tree that is a second, older copy of the
Embedded Systems module, none of it referenced from anywhere. Walking
<organizations> skips all of that for free, so do not be tempted to add a scan
over the zip listing.

What a manifest walk drops is worth checking rather than assuming. The ICEES
export has three Panopto lesopnames under migration/lesopnames/ that appear in
no <item> at all, which reads as content lost; the same three recordings turn
out to be embedded in the three pages the manifest does carry, on the same
Panopto ids. Compare the ids, not the filenames.

The filenames in the package say nothing either. The Evaluatie topic of DeN's
Labo RS485 is stored as "Zonder titel - Copy (1).html", and every
Doelstellingen, Studiemateriaal and Evaluatie topic of the six ICEES labs under
that same name with a numeric id after it: D2L names a file after whatever the
editor last saved. Only the manifest knows the real title, so the staged name
is built from that.

Dropbox quicklinks are recorded as well, with or without instructions, because
in IR most evaluated tasks are a quicklink beside the page that explains them and
orion.json has to name every one of them. So is the visibility of every item: a
module the lector has not opened yet is hidden in the export, and the menu
proposal has to say so.

Came from the course repos, where four copies had drifted: IR had the dropbox
list, the visibility, the start files, the case-insensitive quicklink and the
size limit as a flag; DeN and ICEES had the per-tag rewrite and --fetch-remote.
This is the union.

Stdlib only. Unlike `check` this is an authoring tool: it never runs in CI or
the Stop hook.
"""

from __future__ import annotations

import argparse
import hashlib
import posixpath
import re
import sys
import unicodedata
import zipfile
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from .. import repo

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".avif"}
HTML_EXTS = {".html", ".htm"}

# Documents a page may link and that we therefore self-host, same reasoning as
# for images: a vendor URL dies mid-semester. Slides (.pptx/.ppt) and office
# documents are deliberately absent -- they are course-internal rather than
# something a page links, and they are big: the largest .pptx in a real export
# is 200 MB, past GitHub's 100 MB per-file hard limit. Those stay on Brightspace.
# The list itself is import_brightspace.doc_exts in the course config; this is
# its default, in config.py.

# What a fetched ref may turn out to be. The URL says nothing (a
# DocumentDownloader link has no extension), so the response header decides, and
# anything else -- an HTML error page served with status 200, most of all -- is
# refused rather than written to img/ as a broken picture.
REMOTE_TYPES = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "image/svg+xml": ".svg", "image/bmp": ".bmp",
}

# D2L appends its own numeric id: "74HC_HCT595-datasheet.9581058.pdf".
D2L_ID_RE = re.compile(r"\.\d{5,}$")

# src="..." / href="..." / src='...' -- value captured without the quotes.
ATTR_RE = re.compile(r"""\b(src|href)\s*=\s*(["'])(.*?)\2""", re.IGNORECASE | re.DOTALL)
BODY_RE = re.compile(r"<body\b[^>]*>(.*)</body\s*>", re.IGNORECASE | re.DOTALL)
# An opening tag, so a rewrite can be decided per tag rather than per attribute.
TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)[^>]*>")
# Tags whose src really is an asset. A <script> or an <iframe> is not one:
# OrionCSS's main.js and a YouTube embed belong where they are.
ASSET_TAGS = {"img", "source", "embed"}


def local(tag: str) -> str:
    """Tag name without its XML namespace."""
    return tag.split("}", 1)[-1]


def slugify(text: str, fallback: str = "topic") -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or fallback


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


class Soorten:
    """Which extensions are a document, and which of those a start file.

    Course config, read once in main(): IR self-hosts RobotStudio and CAD files
    into startbestanden/, the other courses only have datasheets.
    """

    def __init__(self, doc_exts, start_exts):
        self.doc = {e.lower() for e in doc_exts}
        self.start = {e.lower() for e in start_exts}

    def kind(self, entry: str) -> str:
        """datasheets/ for a datasheet, startbestanden/ for what a student opens in a tool."""
        return "start" if Path(entry).suffix.lower() in self.start else "doc"


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


class Topic:
    def __init__(self, order: int, title: str, module: list[str], zip_path: str,
                 kind: str = "topic", inline_html: str | None = None,
                 hidden: bool = False):
        self.order = order
        self.hidden = hidden
        self.title = title
        self.module = module
        self.zip_path = zip_path
        # "topic" = an HTML file in the package, "assignment" = a dropbox folder's
        # instructions, which live in dropbox_d2l.xml and have no file of their own.
        self.kind = kind
        self.inline_html = inline_html
        self.staged_name = ""
        self.images_copied = 0
        self.images_reused = 0
        # Not copied out of the package but downloaded from the server the page
        # hotlinked, so the summary can say so: it is the one number that will
        # read differently once that server is gone.
        self.images_fetched = 0
        self.docs_copied = 0
        self.docs_reused = 0
        self.unresolved: list[str] = []


class Document:
    """A datasheet or code bundle, either a topic of its own or linked from a page."""

    def __init__(self, title: str, module: list[str], zip_path: str, hidden: bool = False):
        self.title = title
        self.hidden = hidden
        self.module = module
        self.zip_path = zip_path
        self.staged_name = ""
        self.reused = False
        self.skipped_reason = ""

    @property
    def where(self) -> str:
        return " > ".join(self.module + [self.title]) if self.module else self.title


def norm_href(href: str) -> str:
    """D2L writes manifest hrefs with Windows separators; zip entries use '/'."""
    return unquote(href).replace("\\", "/").strip()


COURSEFILE_RE = re.compile(r"type=coursefile&(?:amp;)?fileId=([^&\"]+)", re.IGNORECASE)


def load_assignments(zf: zipfile.ZipFile) -> dict[str, tuple[str, str]]:
    """resource_code -> (folder name, instructions HTML) from dropbox_d2l.xml.

    In IR most exercises are not content topics at all, and in DeN and ICEES
    every labo ends in a dropbox: the module tree links straight to an
    assignment folder ("Opgave MS met HP PC", "Opdracht: partitioneren"), and
    whatever the student is told to do lives in that folder's instructions
    rather than in a page. Reading the manifest alone would silently drop every
    one of them.
    """
    entry = next((n for n in zf.namelist()
                  if posixpath.basename(n).lower() == "dropbox_d2l.xml"), None)
    if not entry:
        return {}
    try:
        root = ET.fromstring(zf.read(entry))
    except ET.ParseError:
        return {}

    out: dict[str, tuple[str, str]] = {}
    for folder in root.iter():
        if local(folder.tag) != "folder":
            continue
        code = folder.get("resource_code")
        if not code:
            continue
        text = next((t.text for t in folder.iter()
                     if local(t.tag) == "text" and (t.text or "").strip()), None)
        # The start project of an assignment is not in its text but attached to
        # the folder, as a course-file quicklink. Appended as plain links, so the
        # rewrite below stages the file like any other document.
        attached = []
        for link in folder.iter():
            if local(link.tag) != "link":
                continue
            m = COURSEFILE_RE.search(link.get("url") or "")
            if m:
                attached.append(f'<li><a href="{unquote(m.group(1))}">'
                                f'{link.get("name") or "bijlage"}</a></li>')
        if attached:
            text = (text or "") + ('\n<!-- attachments of the dropbox folder -->\n<ul>\n'
                                   + "\n".join(attached) + "\n</ul>")
        # A folder without instructions still counts: its quicklink is a topic
        # orion.json has to name, even when there is no text to convert.
        out[code.lower()] = (folder.get("name") or "", text or "")
    return out


# D2L writes this parameter both ways in one and the same manifest: "rcode"
# on a topic created in the editor, "rCode" on one that came out of a Course
# Copy. Case-sensitively the ICEES export matched 6 of its 16 quicklinks, and
# the 5 dropboxes among the other 10 (virtualiseren, Linux basis, chmod, chown,
# chgrp) were reported as "skipped" rather than staged: five assignments gone
# with a line in the summary saying a link was not understood.
QUICKLINK_RE = re.compile(r"[?&]rcode=([0-9a-fA-F-]+)", re.IGNORECASE)


class Dropbox:
    """A dropbox quicklink in the module tree, for the orion.json proposal."""

    def __init__(self, name: str, title: str, module: list[str], hidden: bool,
                 has_text: bool):
        self.name, self.title, self.module = name, title, module
        self.hidden, self.has_text = hidden, has_text


def find_manifest(zf: zipfile.ZipFile) -> str | None:
    candidates = [n for n in zf.namelist() if posixpath.basename(n).lower() == "imsmanifest.xml"]
    if not candidates:
        return None
    # Shallowest manifest wins: a nested one belongs to a sub-package.
    return min(candidates, key=lambda n: (n.count("/"), len(n)))


def topics_from_manifest(zf: zipfile.ZipFile, manifest_path: str,
                         skipped: list[tuple[str, str]],
                         documents: list[Document],
                         dropboxes: list[Dropbox],
                         soorten: Soorten) -> list[Topic]:
    """Walk <organizations> so topics come out in the order the course shows them."""
    root = ET.fromstring(zf.read(manifest_path))
    base = posixpath.dirname(manifest_path)
    assignments = load_assignments(zf)
    in_zip = set(zf.namelist())

    resources: dict[str, str] = {}
    for el in root.iter():
        if local(el.tag) != "resource":
            continue
        ident = el.get("identifier")
        if not ident:
            continue
        href = el.get("href")
        if not href:
            files = [f.get("href") for f in el if local(f.tag) == "file" and f.get("href")]
            html = [f for f in files if Path(norm_href(f)).suffix.lower() in HTML_EXTS]
            href = (html or files or [None])[0]
        if href:
            resources[ident] = norm_href(href)

    topics: list[Topic] = []
    counter = [0]

    def emit(title: str, module: list[str], ref: str, hidden: bool) -> None:
        href = resources.get(ref)
        if not href:
            return  # a module header, not a topic

        if Path(href).suffix.lower() in HTML_EXTS:
            zip_path = posixpath.normpath(posixpath.join(base, href)) if base else href
            counter[0] += 1
            topics.append(Topic(counter[0], title or Path(href).stem, module, zip_path,
                                hidden=hidden))
            return

        # A datasheet hanging in the module tree as a topic of its own. It has no
        # page to convert, but the file itself is worth self-hosting.
        if Path(href).suffix.lower() in soorten.doc:
            zip_path = posixpath.normpath(posixpath.join(base, href)) if base else href
            if zip_path in in_zip:
                documents.append(Document(title or Path(href).stem, module, zip_path, hidden))
                return

        # A quicklink. If it points at an assignment folder, its instructions are
        # the exercise text; anything else (quiz, discussion) has no content here.
        m = QUICKLINK_RE.search(href)
        if m and m.group(1).lower() in assignments:
            name, instructions = assignments[m.group(1).lower()]
            dropboxes.append(Dropbox(name, title, module, hidden, bool(instructions)))
            if instructions:
                counter[0] += 1
                topics.append(Topic(counter[0], title or name, module, "dropbox_d2l.xml",
                                    kind="assignment", inline_html=instructions,
                                    hidden=hidden))
            return

        skipped.append((" > ".join(module + [title]), href))

    def walk(item: ET.Element, module: list[str], hidden: bool) -> None:
        title_el = next((c for c in item if local(c.tag) == "title"), None)
        title = (title_el.text or "").strip() if title_el is not None else ""
        ref = item.get("identifierref")
        # A hidden module hides everything under it, whatever the topic says.
        hidden = hidden or (item.get("isvisible") or "True").lower() == "false"
        if ref:
            emit(title, module, ref, hidden)
        child_module = module + [title] if title else module
        for child in item:
            if local(child.tag) == "item":
                walk(child, child_module, hidden)

    orgs = next((el for el in root.iter() if local(el.tag) == "organizations"), None)
    if orgs is not None:
        for org in orgs:
            if local(org.tag) != "organization":
                continue
            for item in org:
                if local(item.tag) == "item":
                    walk(item, [], False)

    return topics


def topics_from_filesystem(zf: zipfile.ZipFile) -> list[Topic]:
    """Fallback for a package with no usable manifest: every .html in the zip."""
    names = sorted(n for n in zf.namelist() if Path(n).suffix.lower() in HTML_EXTS)
    topics = []
    for i, name in enumerate(names, start=1):
        module = posixpath.dirname(name).split("/") if posixpath.dirname(name) else []
        topics.append(Topic(i, Path(name).stem, [m for m in module if m], name))
    return topics


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------


class AssetStore:
    """Copies images into img/ and documents into datasheets/ or startbestanden/,
    reusing anything already byte-identical there so a re-import never duplicates
    a datasheet."""

    def __init__(self, zf: zipfile.ZipFile, img_dir: Path, doc_dir: Path, start_dir: Path,
                 dry_run: bool, max_bytes: int, fetch_remote: bool = False):
        self.zf = zf
        self.dirs = {"img": img_dir, "doc": doc_dir, "start": start_dir}
        self.dry_run = dry_run
        self.max_bytes = max_bytes
        self.fetch_remote = fetch_remote
        # Keyed per kind so an image and a document can never collide.
        self.by_hash: dict[tuple[str, str], str] = {}
        self.taken: dict[str, set[str]] = {"img": set(), "doc": set(), "start": set()}

        for kind, dest in self.dirs.items():
            if dest.is_dir():
                for existing in dest.iterdir():
                    if existing.is_file():
                        self.taken[kind].add(existing.name.lower())
                        self.by_hash.setdefault((kind, sha1(existing.read_bytes())),
                                                existing.name)

        # Zip lookups: exact normalized path, and basename for last-resort matching.
        self.exact = {n.lower().lstrip("/"): n for n in zf.namelist()}
        self.by_base: dict[str, list[str]] = {}
        for n in zf.namelist():
            self.by_base.setdefault(posixpath.basename(n).lower(), []).append(n)

    def locate(self, ref: str, topic_dir: str) -> str | None:
        """Map a src value onto an entry in the zip, or None."""
        path = unquote(urlsplit(ref).path)
        if not path:
            return None

        candidates = []
        if path.startswith("/"):
            candidates.append(path.lstrip("/"))
            # /content/enforced/<orgunit>/labo1/x.png -> labo1/x.png
            m = re.search(r"/content/enforced/[^/]+/(.*)$", path)
            if m:
                candidates.append(m.group(1))
        else:
            joined = posixpath.normpath(posixpath.join(topic_dir, path)) if topic_dir else path
            candidates.append(joined.lstrip("./"))
            candidates.append(path)

        for cand in candidates:
            hit = self.exact.get(cand.lower())
            if hit:
                return hit

        # Suffix match: the export sometimes roots paths differently than the topic.
        for cand in candidates:
            tail = cand.lower()
            hits = [n for n in self.zf.namelist() if n.lower().endswith("/" + tail)]
            if len(hits) == 1:
                return hits[0]

        base = posixpath.basename(candidates[0]).lower()
        hits = self.by_base.get(base, [])
        return hits[0] if len(hits) == 1 else None

    def fetch(self, url: str, name_hint: str) -> tuple[str, bool] | None:
        """Download a ref the package does not contain, or None.

        Only useful while the old server is still up, which is the whole point of
        doing it now: the moment it goes down the picture is gone from a page that
        will still render, minus one image. Off unless --fetch-remote is given,
        because an authoring script should not reach out over the network unasked.
        """
        if not self.fetch_remote:
            return None
        url = unescape(url).strip()
        if not url.lower().startswith(("http://", "https://")):
            return None
        try:
            req = Request(url, headers={"User-Agent": "import-brightspace"})
            with urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    return None
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                data = resp.read(self.max_bytes + 1)
        except (URLError, OSError, ValueError):
            return None
        if len(data) > self.max_bytes:
            return None
        ext = REMOTE_TYPES.get(ctype.lower())
        if not ext:
            return None
        # The old platform names nothing, so the id in the query string is the
        # only stable thing about the file: .../?...&object=9400329&...
        m = re.search(r"[?&]object=(\d+)", url)
        return self.stage_bytes(data, name_hint, ext, m.group(1) if m else "", "img")

    def stage(self, entry: str, name_hint: str, kind: str = "img") -> tuple[str, bool]:
        """Copy entry into its folder. Returns (filename, reused_existing)."""
        basename = posixpath.basename(entry)
        return self.stage_bytes(self.zf.read(entry), name_hint,
                                Path(basename).suffix.lower(), Path(basename).stem, kind)

    def stage_bytes(self, data: bytes, name_hint: str, ext: str, stem: str,
                    kind: str = "img") -> tuple[str, bool]:
        digest = sha1(data)
        if (kind, digest) in self.by_hash:
            return self.by_hash[(kind, digest)], True

        ext = ext or (".pdf" if kind == "doc" else ".png")

        if kind in ("doc", "start"):
            # A datasheet is shared across labs, so it is named after the document
            # rather than after the page that happened to link it first.
            name = slugify(D2L_ID_RE.sub("", name_hint or stem), "document") + ext
        else:
            name = f"{slugify(name_hint)}-{slugify(stem, 'afbeelding')}{ext}"
        if len(name) > 80:
            name = name[: 80 - len(ext)] + ext
        n = 2
        while name.lower() in self.taken[kind]:
            name = f"{Path(name).stem}-{n}{ext}"
            n += 1

        if not self.dry_run:
            self.dirs[kind].mkdir(parents=True, exist_ok=True)
            (self.dirs[kind] / name).write_bytes(data)
        self.taken[kind].add(name.lower())
        self.by_hash[(kind, digest)] = name
        return name, False


# --------------------------------------------------------------------------
# Page rewriting
# --------------------------------------------------------------------------


def decode(data: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def rewrite(html: str, topic: Topic, assets: AssetStore, soorten: Soorten,
            img_prefix: str, doc_prefix: str, start_prefix: str) -> str:
    """Point every asset reference in a topic at a local copy.

    Rewriting is decided per tag, not per attribute, because the two cases pull
    in opposite directions. The src of an <img> is an asset whatever it looks
    like, so it is chased even without an extension: DeN's Packet Tracer pages
    carry their screenshots as DocumentDownloader URLs on
    chamilo-downloads.hogent.be, the platform the courses lived on before
    Brightspace. Those end in "&display=1" rather than ".png" and carry an
    expiring security_code, so judging them on their extension would let exactly
    the hotlink we are trying to remove pass through silently. An href, on the
    other hand, is chased only when it points at a document worth self-hosting,
    and a <script> or an <iframe> is left alone entirely: a YouTube embed and
    OrionCSS's main.js are not assets and must not be reported as missing.

    A Chamilo link in an href is reported rather than left alone. It carries no
    extension and points at nothing in the package, so it is listed for a person
    to replace with the file under startbestanden/ or datasheets/; IR's start
    projects were linked that way.
    """
    topic_dir = posixpath.dirname(topic.zip_path)

    def attrs(tag_html: str, tag: str) -> str:
        def repl(m: re.Match[str]) -> str:
            attr, quote, value = m.group(1), m.group(2), m.group(3)
            raw = value.strip()
            if not raw or raw.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
                return m.group(0)

            ext = Path(unquote(urlsplit(raw).path)).suffix.lower()
            is_img, is_doc = ext in IMAGE_EXTS, ext in soorten.doc
            looks_remote = raw.lower().startswith(("http://", "https://", "//"))
            if attr.lower() == "src":
                if tag not in ASSET_TAGS:
                    return m.group(0)
            elif looks_remote and "chamilo" in raw.lower():
                topic.unresolved.append(raw)
                return m.group(0)
            elif not is_img and not is_doc:
                return m.group(0)

            entry = assets.locate(raw, topic_dir)
            if not entry:
                # Not in the package. It may still be reachable on the server the
                # page hotlinks, and if it is, now is the only time we will get it.
                got = assets.fetch(raw, topic.title) if attr.lower() == "src" else None
                if not got:
                    topic.unresolved.append(raw)
                    return m.group(0)
                name, reused = got
                topic.images_reused += reused
                topic.images_fetched += not reused
                return f'{attr}={quote}{img_prefix}{name}{quote}'

            # Trust the resolved entry over the URL: a Brightspace download link
            # carries no extension, so only the zip entry says what it really is.
            if Path(posixpath.basename(entry)).suffix.lower() in soorten.doc:
                # A document is shared across labs, so it keeps its own name rather
                # than being named after whichever page linked it first.
                kind = soorten.kind(entry)
                name, reused = assets.stage(entry, "", kind)
                topic.docs_reused += reused
                topic.docs_copied += not reused
                prefix = doc_prefix if kind == "doc" else start_prefix
                return f'{attr}={quote}{prefix}{name}{quote}'

            name, reused = assets.stage(entry, topic.title, "img")
            topic.images_reused += reused
            topic.images_copied += not reused
            return f'{attr}={quote}{img_prefix}{name}{quote}'

        return ATTR_RE.sub(repl, tag_html)

    def per_tag(m: re.Match[str]) -> str:
        return attrs(m.group(0), m.group(1).lower())

    return TAG_RE.sub(per_tag, html)


def header(topic: Topic, img_prefix: str, doc_prefix: str) -> str:
    module = " > ".join(topic.module) if topic.module else "(geen module)"
    unresolved = f"\n     unresolved: {len(topic.unresolved)} ({', '.join(topic.unresolved[:3])})" if topic.unresolved else ""
    docs = ""
    if topic.docs_copied or topic.docs_reused:
        docs = (f"\n     docs:   {topic.docs_copied} copied, {topic.docs_reused} reused, "
                f"rewritten to {doc_prefix}*")
    return (
        "<!-- imported-from-brightspace\n"
        f"     title:  {topic.title}\n"
        f"     module: {module}\n"
        f"     order:  {topic.order}\n"
        f"     hidden: {'yes (not opened in Brightspace at export time)' if topic.hidden else 'no'}\n"
        f"     kind:   {topic.kind}"
        f"{'  (Brightspace assignment: needs an indienen section)' if topic.kind == 'assignment' else ''}\n"
        f"     source: {topic.zip_path}\n"
        f"     images: {topic.images_copied} copied, {topic.images_reused} reused, "
        f"rewritten to {img_prefix}*{docs}{unresolved}\n"
        "-->\n"
    )


def worklist(topics: list[Topic], documents: list[Document], doc_dir: Path,
             start_dir: Path, dropboxes: list[Dropbox], soorten: Soorten) -> str:
    lines = [
        "# Import worklist",
        "",
        f"{len(topics)} topics staged from the Brightspace export. Convert each one with the",
        "orion-convert skill, then add it as a page in `orion.json` and run",
        "`python ../OrionTools/orion.py check`. Delete a row once its page has its place in the repo.",
        "",
        "| # | Module | Titel | Soort | Verborgen | Staged | Afb. | Doc. | Onopgelost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in topics:
        module = " &gt; ".join(t.module) if t.module else "-"
        imgs = t.images_copied + t.images_reused
        docs = t.docs_copied + t.docs_reused
        lines.append(
            f"| {t.order} | {module} | {t.title} | {t.kind} | {'ja' if t.hidden else '-'} "
            f"| [{t.staged_name}]({t.staged_name}) "
            f"| {imgs or '-'} | {docs or '-'} | {len(t.unresolved) or '-'} |"
        )

    staged = [d for d in documents if d.staged_name]
    if staged:
        mappen = f"`{doc_dir.name}/`"
        if soorten.start:
            mappen += f" en `{start_dir.name}/`"
        lines += [
            "",
            f"## Documenten in {mappen}",
            "",
            "Deze staan al op hun plaats. Geef ze gerust een kortere naam en link ze",
            "vanuit de pagina's die erover gaan. Vergeet `git add` niet.",
            "",
            "| Waar het stond | Bestand | Verborgen | Nieuw? |",
            "|---|---|---|---|",
        ]
        for d in staged:
            folder = doc_dir.name if soorten.kind(d.zip_path) == "doc" else start_dir.name
            lines.append(f"| {d.where.replace('>', '&gt;')} | `{folder}/{d.staged_name}` "
                         f"| {'ja' if d.hidden else '-'} "
                         f"| {'hergebruikt' if d.reused else 'nieuw'} |")

    ignored = [d for d in documents if d.skipped_reason]
    if ignored:
        lines += ["", "### Overgeslagen documenten", ""]
        for d in ignored:
            lines.append(f"- {d.where}: {d.skipped_reason}")

    if dropboxes:
        lines += [
            "",
            "## Dropbox-quicklinks",
            "",
            "Elk van deze wordt een `dropbox`-topic in `orion.json`, met de mapnaam als naam.",
            "",
            "| Module | Titel in het menu | Dropboxnaam | Verborgen | Instructies |",
            "|---|---|---|---|---|",
        ]
        for b in dropboxes:
            module = " &gt; ".join(b.module) if b.module else "-"
            lines.append(f"| {module} | {b.title} | {b.name} | {'ja' if b.hidden else '-'} "
                         f"| {'ja, gestaged' if b.has_text else '-'} |")

    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="orion.py import-brightspace", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    repo.voeg_repo_toe(ap)
    ap.add_argument("zip", type=Path, help="the Brightspace export .zip")
    ap.add_argument("--outdir", type=Path, default=None,
                    help="where to stage the raw topic HTML (default: paths.incoming)")
    ap.add_argument("--img-dir", type=Path, default=None,
                    help="where to copy course images (default: paths.img)")
    ap.add_argument("--img-prefix", default=None,
                    help="what the rewritten src should point at (default: "
                         "import_brightspace.page_depth times ../, then paths.img; "
                         "correct for a page that deep, a page one level up needs one ../ less)")
    ap.add_argument("--doc-dir", type=Path, default=None,
                    help="where to copy datasheets and other documents (default: paths.datasheets)")
    ap.add_argument("--doc-prefix", default=None,
                    help="what a rewritten document href should point at "
                         "(default: as --img-prefix, with paths.datasheets)")
    ap.add_argument("--start-dir", type=Path, default=None,
                    help="where to copy the start files of import_brightspace.start_exts "
                         "(default: paths.startbestanden)")
    ap.add_argument("--start-prefix", default=None,
                    help="what a rewritten start-file href should point at "
                         "(default: as --img-prefix, with paths.startbestanden)")
    ap.add_argument("--max-mb", type=int, default=None,
                    help="skip a document larger than this (default: import_brightspace.max_mb)")
    ap.add_argument("--only", metavar="TEXT",
                    help="stage only topics whose module path or title contains TEXT "
                         "(case-insensitive), e.g. --only 'Managed Switch'")
    ap.add_argument("--fetch-remote", action="store_true",
                    help="download image refs the package does not contain from the "
                         "server the page hotlinks (chamilo-downloads.hogent.be), "
                         "instead of only reporting them. Off by default: it is the "
                         "one thing here that touches the network.")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    vak = repo.vind(args)
    cfg = vak.config["import_brightspace"]
    paden = vak.config["paths"]
    soorten = Soorten(cfg["doc_exts"], cfg["start_exts"])
    omhoog = "../" * cfg["page_depth"]

    def prefix(sleutel):
        return omhoog + paden[sleutel].strip("/") + "/"

    outdir = args.outdir or vak.pad("incoming")
    img_dir = args.img_dir or vak.pad("img")
    doc_dir = args.doc_dir or vak.pad("datasheets")
    start_dir = args.start_dir or vak.pad("startbestanden")
    img_prefix = args.img_prefix if args.img_prefix is not None else prefix("img")
    doc_prefix = args.doc_prefix if args.doc_prefix is not None else prefix("datasheets")
    start_prefix = (args.start_prefix if args.start_prefix is not None
                    else prefix("startbestanden"))
    max_mb = args.max_mb if args.max_mb is not None else cfg["max_mb"]

    if not args.zip.is_file():
        print(f"import-brightspace: no such file: {args.zip}", file=sys.stderr)
        return 2

    with zipfile.ZipFile(args.zip) as zf:
        skipped: list[tuple[str, str]] = []
        documents: list[Document] = []
        dropboxes: list[Dropbox] = []
        max_bytes = max_mb * 1024 * 1024
        manifest = find_manifest(zf)
        if manifest:
            topics = topics_from_manifest(zf, manifest, skipped, documents, dropboxes, soorten)
            source = f"manifest {manifest}"
        else:
            topics = []
            source = ""
        if not topics:
            topics = topics_from_filesystem(zf)
            source = "filesystem scan (no usable manifest)"

        if not topics:
            print("import-brightspace: no HTML topics found in the package", file=sys.stderr)
            return 1

        total = len(topics)
        if args.only:
            needle = args.only.lower()
            topics = [t for t in topics
                      if needle in (" > ".join(t.module) + " " + t.title).lower()]
            skipped[:] = [s for s in skipped if needle in s[0].lower()]
            documents[:] = [d for d in documents if needle in d.where.lower()]
            dropboxes[:] = [b for b in dropboxes
                            if needle in (" > ".join(b.module) + " " + b.title).lower()]
            if not topics:
                print(f"import-brightspace: --only {args.only!r} matched none of "
                      f"{total} topics", file=sys.stderr)
                return 1
            source += f" (--only {args.only!r}: {len(topics)} of {total})"

        assets = AssetStore(zf, img_dir, doc_dir, start_dir, args.dry_run, max_bytes,
                            fetch_remote=args.fetch_remote)
        if not args.dry_run:
            outdir.mkdir(parents=True, exist_ok=True)

        # Documents that hang in the module tree as a topic of their own. They
        # have no page to convert, so they are staged here rather than in the
        # per-topic loop below.
        for doc in documents:
            try:
                info = zf.getinfo(doc.zip_path)
            except KeyError:
                doc.skipped_reason = f"{doc.zip_path} zit niet in de zip"
                continue
            if info.file_size > max_bytes:
                doc.skipped_reason = (
                    f"{posixpath.basename(doc.zip_path)} is "
                    f"{info.file_size / 1024 / 1024:.0f} MB, boven de limiet van "
                    f"{max_mb} MB")
                continue
            doc.staged_name, doc.reused = assets.stage(doc.zip_path, doc.title,
                                                       soorten.kind(doc.zip_path))

        seen: set[str] = set()
        for topic in topics:
            if topic.inline_html is not None:
                raw = topic.inline_html
            else:
                try:
                    raw = decode(zf.read(topic.zip_path))
                except KeyError:
                    topic.unresolved.append(f"(missing in zip: {topic.zip_path})")
                    topic.staged_name = "-"
                    continue

            body = BODY_RE.search(raw)
            content = body.group(1).strip() if body else raw.strip()
            content = rewrite(content, topic, assets, soorten, img_prefix, doc_prefix,
                              start_prefix)

            name = f"{topic.order:03d}-{slugify(topic.title)}.html"
            while name.lower() in seen:
                name = f"{Path(name).stem}-x.html"
            seen.add(name.lower())
            topic.staged_name = name

            if not args.dry_run:
                (outdir / name).write_text(
                    header(topic, img_prefix, doc_prefix) + content + "\n",
                    encoding="utf-8")

        if not args.dry_run:
            (outdir / "WORKLIST.md").write_text(
                worklist(topics, documents, doc_dir, start_dir, dropboxes, soorten),
                encoding="utf-8")

    copied = sum(t.images_copied for t in topics)
    reused = sum(t.images_reused for t in topics)
    fetched = sum(t.images_fetched for t in topics)
    doc_copied = sum(t.docs_copied for t in topics) + sum(
        1 for d in documents if d.staged_name and not d.reused)
    doc_reused = sum(t.docs_reused for t in topics) + sum(
        1 for d in documents if d.staged_name and d.reused)
    doc_ignored = [d for d in documents if d.skipped_reason]
    unresolved = [(t, r) for t in topics for r in t.unresolved]

    doc_dirs = f"{doc_dir} or {start_dir}" if soorten.start else f"{doc_dir}"
    prefix_txt = "would stage" if args.dry_run else "staged"
    assignments = sum(1 for t in topics if t.kind == "assignment")
    print(f"import-brightspace: {prefix_txt} {len(topics)} topics from {source}")
    print(f"  -> {outdir}{'' if args.dry_run else '/ (+ WORKLIST.md)'}")
    print(f"  {len(topics) - assignments} content pages, {assignments} assignment descriptions")
    print(f"  images: {copied} copied into {img_dir}, {reused} reused (already in the repo)")
    if fetched:
        print(f"  {fetched} images were not in the package and were downloaded from "
              f"the server the page hotlinked")
    elif not args.fetch_remote and any("http" in r for t in topics for r in t.unresolved):
        print("  Some refs point at a server outside the package. Re-run with "
              "--fetch-remote to pull them in while that server is still up.")
    print(f"  documents: {doc_copied} copied into {doc_dirs}, "
          f"{doc_reused} reused (already in the repo)")
    print(f"  dropbox quicklinks: {len(dropboxes)} "
          f"({sum(1 for b in dropboxes if b.has_text)} with instructions, staged as a page)")

    if doc_ignored:
        print(f"  {len(doc_ignored)} documents skipped:")
        for d in doc_ignored:
            print(f"    {d.where}: {d.skipped_reason}")

    if skipped:
        print(f"  {len(skipped)} items carried no importable HTML "
              f"(PDF/PPTX attachment, quiz, discussion, ...):")
        for title, href in skipped[:8]:
            print(f"    {title}  [{posixpath.basename(href.split('?')[0]) or href}]")
        if len(skipped) > 8:
            print(f"    ... and {len(skipped) - 8} more")

    if unresolved:
        print(f"  {len(unresolved)} asset refs could not be resolved in the package:")
        for topic, ref in unresolved[:15]:
            print(f"    {topic.staged_name}: {ref}")
        if len(unresolved) > 15:
            print(f"    ... and {len(unresolved) - 15} more")
        print("  Those refs were left as-is; `orion.py check` will flag them.")

    staged_dirs = [d.name for d, n in
                   ((img_dir, copied), (doc_dir, doc_copied),
                    (start_dir, doc_copied if soorten.start else 0)) if n]
    if not args.dry_run and staged_dirs:
        print(f"  Remember to 'git add {'/ '.join(staged_dirs)}/' -- "
              "`orion.py check` only accepts assets tracked by git.")
    return 0
